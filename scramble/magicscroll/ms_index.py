# ms_index.py
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

# LlamaIndex core imports
from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    Settings,
    load_index_from_storage,
)
# Redis imports

from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.storage.index_store.redis import RedisIndexStore
# Vector store and embeddings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import VectorStoreQuery
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# ChromaDB
import chromadb
import redis

# Local imports
from .ms_entry import MSEntry, EntryType

logger = logging.getLogger(__name__)

class MSIndexBase(ABC):
    """Abstract base class for MagicScroll indices."""
    
    @abstractmethod
    async def add_entry(self, entry: MSEntry) -> bool:
        """
        Add an entry to the index.
        Returns True if successful.
        """
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
        """
        Search for entries.
        Returns list of matches with scores.
        """
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

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize LlamaIndex implementation."""
        self.storage_path = storage_path or Path.home() / '.scramble' / 'scroll'
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB for vector store
        chroma_path = self.storage_path / 'chroma'
        chroma_path.mkdir(exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        self.collection = self.chroma_client.get_or_create_collection("scroll-store")
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        
        # Initialize Redis document store
        self.doc_store = RedisDocumentStore.from_host_and_port(host='localhost', port=6379, namespace='scramble')

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
                
        # Create storage context with both stores
        try:
            logger.info("Initializing storage context with Redis and ChromaDB")
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store,
                docstore=self.doc_store,
                persist_dir=str(self.storage_path)  # Add persist_dir here
            )
            
            # Try to load existing index
            try:
                self.index = load_index_from_storage(
                    storage_context=self.storage_context,
                    persist_dir=str(self.storage_path)  # Add persist_dir here
                )
                logger.info("Successfully loaded existing index")
            except Exception as load_err:
                logger.info(f"No existing index found, creating new one: {load_err}")
                self.index = VectorStoreIndex.from_documents(
                    [],
                    storage_context=self.storage_context,
                    show_progress=True
                )
                # Persist the new index
                self.index.storage_context.persist(persist_dir=str(self.storage_path))
                logger.info("Created and persisted new index")
            
        except Exception as e:
            logger.error(f"Error initializing storage: {e}")
            raise


    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to the index."""
        try:
             # Add debug logging for ChromaDB collection size
            collection_size = self.collection.count()
            logger.info(f"Current ChromaDB collection size: {collection_size}")
        
            # Check if we already have a version of this content
            existing_docs = self.index.storage_context.docstore.docs
            for doc_id, doc in existing_docs.items():
                if doc.get_content() == entry.content:
                    logger.debug(f"Content already exists in doc {doc_id}, skipping")
                    return True
                    
            # Create LlamaIndex document
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
                extra_info=MSEntry.sanitize_metadata_for_chroma(entry.to_dict())
            )
            
            # Add to index
            self.index.insert(doc)
            
            # Persist changes
            self.index.storage_context.persist(persist_dir=str(self.storage_path))
            
            logger.debug(f"Successfully added entry {entry.id} to index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding entry to index: {e}")
            return False
            

    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get a specific entry."""
        try:
            doc = self.index.storage_context.docstore.get_document(entry_id)
            if doc and isinstance(doc.metadata, dict):
                return MSEntry.from_dict(doc.metadata)
        except Exception as e:
            logger.error(f"Error retrieving entry {entry_id}: {e}")
        return None
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        try:
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
            
            # Debug: Let's check what's in our index
            logger.info("Checking index contents:")
            try:
                all_docs = self.index.storage_context.docstore.docs
                logger.info(f"Documents in store: {len(all_docs)}")
                for doc_id, doc in all_docs.items():
                    logger.info(f"Doc ID: {doc_id}")
                   
            except Exception as e:
                logger.error(f"Error checking docs: {e}")
            
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
                logger.info(f"Processing node with ID: {node.node_id}")
                logger.info(f"Node score: {getattr(node, 'score', 'No score')}")
                logger.info(f"Node metadata: {getattr(node, 'metadata', 'No metadata')}")
                
                if hasattr(node, 'score') and node.score < min_score:
                    logger.debug(f"Skipping node due to low score: {node.score}")
                    continue
                    
                try:
                    # Get the metadata and verify it
                    metadata = getattr(node, 'metadata', {})
                    logger.info(f"Raw metadata: {metadata}")

                    if not metadata:
                        logger.warning(f"No metadata for node {node.node_id}")
                        continue

                    entry = MSEntry.from_dict(metadata)
                    result = {
                        "entry": entry,
                        "score": getattr(node, 'score', 1.0),
                        "relevance_score": getattr(node, 'relevance_score', 1.0)
                    }
                    results.append(result)
                    logger.info(f"Added result: {result}")
                 
                except Exception as e:
                    logger.error(f"Error processing node {node.node_id}: {e}", exc_info=True)
            

            # Sort by score and limit results
            results.sort(key=lambda x: x["score"], reverse=True)
            final_results = results[:limit]
            logger.info(f"Final results: {len(final_results)}")
            for i, r in enumerate(final_results):
                logger.info(f"Result {i}: score={r['score']}, content={r['entry'].content[:50]}...")
                
            return final_results
                
        except Exception as e:
            logger.error(f"Error searching index: {e}", exc_info=True)
            return []
    

    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        try:
            metadata_filter = {}
            
            # Add time filter if specified
            if hours is not None:
                cutoff = datetime.utcnow().timestamp() - (hours * 3600)
                metadata_filter["created_at"] = {"$gt": cutoff}
            
            # Add type filter if specified
            if entry_types:
                metadata_filter["type"] = {"$in": [t.value for t in entry_types]}
            
            # Get all matching documents
            # Note: This could be optimized with proper time indexing
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