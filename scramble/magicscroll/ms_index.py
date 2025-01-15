"""LlamaIndex implementation for MagicScroll."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone  
from pathlib import Path
from typing import List, Dict, Any, Optional, cast
import json
from scramble.utils.logging import get_logger

# LlamaIndex core imports
from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    Settings,
    load_index_from_storage,
)

# Database imports
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import VectorStoreQuery
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Local imports
from scramble.config import Config
from .ms_entry import MSEntry, EntryType
from .chroma_client import AsyncChromaClient, ChromaCollection

logger = get_logger(__name__)

class MSIndexBase(ABC):
    """Abstract base class for MagicScroll indices."""
    
    @abstractmethod
    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to the index."""
        pass
    
    @abstractmethod
    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get a specific entry by ID."""
        pass
    
    @abstractmethod
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        pass
    
    @abstractmethod
    async def search(self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for entries."""
        pass
    
    @abstractmethod
    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        pass
    
    @abstractmethod
    async def get_chain(self, entry_id: str) -> List[MSEntry]:
        """Get chain of entries connected by parent_id."""
        pass

class LlamaIndexImpl(MSIndexBase):
    """LlamaIndex implementation of MagicScroll index."""

    def __init__(self):
        """Initialize basic attributes."""
        self.config = Config()
        self.storage_path: Optional[Path] = None
        self.vector_store: Optional[ChromaVectorStore] = None
        self.doc_store: Optional[RedisDocumentStore] = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[VectorStoreIndex] = None

    @classmethod
    async def create(cls, chroma_client: AsyncChromaClient, collection: ChromaCollection) -> 'LlamaIndexImpl':
        """Factory method to create and initialize index."""
        instance = cls()
        
        try:
            # Set up storage path
            instance.storage_path = Path.home() / '.scramble' / 'magicscroll'
            instance.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize vector store
            instance.vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # Initialize Redis document store
            instance.doc_store = RedisDocumentStore.from_host_and_port(
                host=instance.config.REDIS_HOST,
                port=instance.config.REDIS_PORT,
                namespace='scramble'
            )
            
            # Initialize embedding model and settings
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-large-en-v1.5",
                embed_batch_size=32
            )
            Settings.node_parser = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=50
            )
            Settings.llm = None  # Disable LLM usage
            
            # Initialize storage context
            instance.storage_context = StorageContext.from_defaults(
                vector_store=instance.vector_store,
                docstore=instance.doc_store,
                persist_dir=str(instance.storage_path)
            )
            
            # Load or create index
            try:
                loaded_index = load_index_from_storage(
                    storage_context=instance.storage_context,
                    persist_dir=str(instance.storage_path)
                )
                if isinstance(loaded_index, VectorStoreIndex):
                    instance.index = loaded_index
                else:
                    instance.index = cast(VectorStoreIndex, loaded_index)
                logger.info("Loaded existing index")
                
            except Exception:
                instance.index = VectorStoreIndex(
                    [],
                    storage_context=instance.storage_context,
                    show_progress=True
                )
                logger.info("Created new index")
            
            return instance
            
        except Exception as e:
            logger.error(f"Error initializing LlamaIndex: {e}")
            raise

    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to the index."""
        try:
            if not self.index or not self.storage_context:
                return False

            # Create LlamaIndex document
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
                extra_info=MSEntry.sanitize_metadata_for_chroma(entry.to_dict())
            )
            
            # Add to index
            self.index.insert(doc)
            self.storage_context.persist(str(self.storage_path))
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding entry: {e}")
            return False

    async def search(self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for entries using vector store."""
        try:
            if not self.index:
                return []
            
            # Create vector store query
            vector_store_query = VectorStoreQuery(
                query_str=query,
                similarity_top_k=limit  # Get number of requested results
            )
            
            # Get response
            response = await self.index.as_retriever().aretrieve(query)
            
            results = []
            for node in response:
                if hasattr(node, 'score') and node.score < min_score:
                    continue
                    
                if not node.metadata:
                    continue
                    
                try:
                    entry = MSEntry.from_dict(node.metadata)
                    results.append({
                        "entry": entry,
                        "score": getattr(node, 'score', 1.0)
                    })
                except Exception as e:
                    logger.error(f"Error processing node metadata: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching index: {e}")
            return []

    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get a specific entry."""
        try:
            if not self.storage_context:
                return None
                
            doc = self.storage_context.docstore.get_document(entry_id)
            if doc and isinstance(doc.metadata, dict):
                return MSEntry.from_dict(doc.metadata)
                
        except Exception as e:
            logger.error(f"Error getting entry {entry_id}: {e}")
            
        return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        try:
            if not self.index or not self.storage_context:
                return False
                
            self.index.delete_ref_doc(entry_id)
            self.storage_context.persist(str(self.storage_path))
            return True
            
        except Exception as e:
            logger.error(f"Error deleting entry {entry_id}: {e}")
            return False

    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        try:
            if not self.storage_context:
                return []
                
            matching_docs = []
            cutoff = None
            
            if hours is not None:
                cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
                
            # Get all docs and filter
            for doc_id in self.storage_context.docstore.docs:
                doc = self.storage_context.docstore.get_document(doc_id)
                if doc is None or not isinstance(doc.metadata, dict):
                    continue
                    
                # Apply time filter
                if cutoff:
                    created_at = datetime.fromisoformat(doc.metadata.get("created_at", ""))
                    if created_at.timestamp() < cutoff:
                        continue
                        
                # Apply type filter
                if entry_types:
                    doc_type = doc.metadata.get("type")
                    if not doc_type or doc_type not in [t.value for t in entry_types]:
                        continue
                        
                matching_docs.append(doc)
            
            # Sort by creation time
            matching_docs.sort(
                key=lambda x: datetime.fromisoformat(x.metadata["created_at"]),
                reverse=True
            )
            
            return [MSEntry.from_dict(doc.metadata) for doc in matching_docs[:limit]]
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []

    async def get_chain(self, entry_id: str) -> List[MSEntry]:
        """Get chain of entries connected by parent_id."""
        try:
            chain = []
            current_id = entry_id
            visited = set()
            
            while current_id and current_id not in visited:
                visited.add(current_id)
                entry = await self.get_entry(current_id)
                
                if not entry:
                    break
                    
                chain.append(entry)
                current_id = entry.parent_id
            
            return list(reversed(chain))
            
        except Exception as e:
            logger.error(f"Error getting entry chain for {entry_id}: {e}")
            return []