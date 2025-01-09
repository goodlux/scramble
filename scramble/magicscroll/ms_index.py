"""LlamaIndex implementation for MagicScroll."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone  
from pathlib import Path
from typing import List, Dict, Any, Optional
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
        """Add an entry to the index. Returns True if successful."""
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
        """Search for entries. Returns list of matches with scores."""
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
        self.chroma_client: Optional[AsyncChromaClient] = None
        self.collection: Optional[ChromaCollection] = None
        self.vector_store: Optional[ChromaVectorStore] = None
        self.doc_store: Optional[RedisDocumentStore] = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[VectorStoreIndex] = None

    @classmethod
    async def create(cls, chroma_client: AsyncChromaClient, collection: ChromaCollection) -> 'LlamaIndexImpl':
        """Factory method to create and initialize index asynchronously."""
        instance = cls()
        
        try:
            # Set up storage path and required directories first
            instance.storage_path = Path.home() / '.scramble' / 'magicscroll'
            instance.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Create required subdirectories
            docstore_path = instance.storage_path / 'docstore'
            docstore_path.mkdir(exist_ok=True)
            vector_store_path = instance.storage_path / 'vector_store'
            vector_store_path.mkdir(exist_ok=True)
            
            # Create minimal index_store.json if it doesn't exist
            index_store_path = instance.storage_path / 'index_store.json'
            if not index_store_path.exists():
                logger.info("Creating initial index store file")
                initial_store = {
                    "index_store": {},
                    "vector_store": {},
                    "document_store": {}
                }
                with open(index_store_path, 'w') as f:
                    json.dump(initial_store, f)
            
            # Initialize ChromaDB with async client
            instance.chroma_client = chroma_client
            instance.collection = collection
            instance.vector_store = ChromaVectorStore(
                chroma_collection=collection
            )
            
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
            Settings.llm = None  # Explicitly disable LLM usage
            
            # Create storage context
            logger.info("Initializing storage context with Redis and ChromaDB")
            instance.storage_context = StorageContext.from_defaults(
                vector_store=instance.vector_store,
                docstore=instance.doc_store,
                persist_dir=str(instance.storage_path)
            )
            
            # First time running - no existing index
            if not (instance.storage_path / 'index_store.json').exists():
                logger.info("No existing index found, creating new one")
                instance.index = VectorStoreIndex(
                    [],
                    storage_context=instance.storage_context,
                    show_progress=True
                )
            else:
                # Try to load existing index
                try:
                    loaded_index = load_index_from_storage(
                        storage_context=instance.storage_context,
                        persist_dir=str(instance.storage_path)
                    )
                    if not isinstance(loaded_index, VectorStoreIndex):
                        logger.warning("Loaded index is not VectorStoreIndex, creating new one")
                        instance.index = VectorStoreIndex(
                            [],
                            storage_context=instance.storage_context,
                            show_progress=True
                        )
                    else:
                        instance.index = loaded_index
                        logger.info("Successfully loaded existing index")
                except Exception as load_err:
                    logger.warning(f"Error loading existing index, creating new one: {load_err}")
                    instance.index = VectorStoreIndex(
                        [],
                        storage_context=instance.storage_context,
                        show_progress=True
                    )
            
            logger.debug(f"Collection exists: {instance.collection is not None}")
            logger.debug(f"Index exists: {instance.index is not None}")
            return instance
            
        except Exception as e:
            logger.error(f"Error initializing LlamaIndex: {e}")
            raise RuntimeError(f"Failed to initialize LlamaIndex: {str(e)}")

    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to the index."""
        try:
            if not self.collection or not self.index:
                logger.error("Collection or index not initialized")
                return False

            # Add debug logging for ChromaDB collection size
            count = await self.collection.count()
            logger.info(f"Current ChromaDB collection size: {count}")
            
            if not self.index.storage_context:
                logger.error("Storage context not initialized")
                return False
                
            # Check if we already have a version of this content
            existing_docs = self.index.storage_context.docstore.docs
            for doc_id, doc in existing_docs.items():
                if doc.get_content() == entry.content:
                    logger.debug(f"Content already exists in doc {doc_id}, skipping")
                    return True
                    
            # Create LlamaIndex document with proper metadata
            metadata_dict = MSEntry.sanitize_metadata_for_chroma(entry.to_dict())
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
                extra_info=metadata_dict  # Changed to extra_info
            )
            # Get embedding
            embedding = Settings.embed_model.get_text_embedding(entry.content)
            
            # Add to collection using proper metadata key
            await self.collection.add(
                embeddings=[embedding],
                metadata_list=[metadata_dict],  
                documents=[entry.content],
                ids=[entry.id]
            )
            # Add to document store
            if self.index.storage_context:
                self.index.storage_context.docstore.add_documents([doc])
                self.index.storage_context.persist(persist_dir=str(self.storage_path))
            
            logger.debug(f"Successfully added entry {entry.id} to index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding entry to index: {e}")
            return False
            
    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get a specific entry."""
        try:
            if not self.index or not self.index.storage_context:
                return None
                
            doc = self.index.storage_context.docstore.get_document(entry_id)
            if doc and isinstance(doc.metadata, dict):
                return MSEntry.from_dict(doc.metadata)
        except Exception as e:
            logger.error(f"Error retrieving entry {entry_id}: {e}")
        return None
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        try:
            if not self.index or not self.index.storage_context:
                return False
                
            self.index.delete_ref_doc(entry_id)
            self.index.storage_context.persist(str(self.storage_path))
            logger.debug(f"Successfully deleted entry {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting entry {entry_id}: {e}")
            return False
    
    async def search(self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search for entries."""
        try:
            if not self.index:
                return []
                
            logger.info(f"Beginning search for query: {query}")
            
            # Build metadata filter if entry types specified
            metadata_filter = None
            if entry_types:
                metadata_filter = {
                    "type": {"$in": [t.value for t in entry_types]}
                }
                logger.debug(f"Using metadata filter: {metadata_filter}")
            
            # Create query
            vector_store_query = VectorStoreQuery(
                query_str=query,
                similarity_top_k=limit * 2  # Get extra results for score filtering
            )
            logger.debug(f"Created vector store query: {vector_store_query}")
            
            # Execute query without OpenAI dependency
            query_engine = self.index.as_query_engine(
                vector_store_query=vector_store_query,
                similarity_top_k=limit * 2,
                response_synthesizer=None  # This prevents OpenAI usage
            )
            logger.info("Executing query...")
            query_result = query_engine.query(query)
            logger.info(f"Query completed. Source nodes: {len(query_result.source_nodes)}")
            
            # Process results
            results = []
            for node in query_result.source_nodes:
                if hasattr(node, 'score') and node.score < min_score:
                    continue
                    
                try:
                    metadata = getattr(node, 'metadata', {})
                    if not metadata:
                        continue

                    entry = MSEntry.from_dict(metadata)
                    result = {
                        "entry": entry,
                        "score": getattr(node, 'score', 1.0),
                        "relevance_score": getattr(node, 'relevance_score', 1.0)
                    }
                    results.append(result)
                 
                except Exception as e:
                    logger.error(f"Error processing node {node.node_id}: {e}")
            
            # Sort by score and limit results
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
                
        except Exception as e:
            logger.error(f"Error searching index: {e}")
            return []
    
    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        try:
            if not self.index or not self.index.storage_context:
                return []
                
            metadata_filter = {}
            
            # Add time filter if specified
            if hours is not None:
                cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
                metadata_filter["created_at"] = {"$gt": cutoff}
            
            # Add type filter if specified
            if entry_types:
                metadata_filter["type"] = {"$in": [t.value for t in entry_types]}
            
            # Get all matching documents
            matching_docs = []
            for doc_id in self.index.storage_context.docstore.docs:
                doc = self.index.storage_context.docstore.get_document(doc_id)
                if doc is not None and self._matches_filter(doc.metadata, metadata_filter):
                    matching_docs.append(doc)
            
            # Sort by creation time and convert to entries
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
            
            return list(reversed(chain))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Error getting entry chain for {entry_id}: {e}")
            return []
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Helper to check if metadata matches a filter dictionary."""
        for key, filter_value in filter_dict.items():
            if key not in metadata:
                return False
                
            if isinstance(filter_value, dict):
                # Handle operators like $gt, $lt, $in
                for op, val in filter_value.items():
                    if op == "$gt" and metadata[key] <= val:
                        return False
                    elif op == "$lt" and metadata[key] >= val:
                        return False
                    elif op == "$in" and metadata[key] not in val:
                        return False
            elif metadata[key] != filter_value:
                return False
                
        return True