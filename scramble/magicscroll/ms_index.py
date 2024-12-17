# ms_index.py
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    Document,
    StorageContext,
    load_index_from_storage
)
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index.vector_stores import ChromaVectorStore, VectorStoreQuery
import chromadb


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
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma
        self.chroma_client = chromadb.PersistentClient(path=str(storage_path))
        self.collection = self.chroma_client.get_or_create_collection("magicscroll")
        
        # Create vector store
        vector_store = ChromaVectorStore(chroma_collection=self.collection)
        
        # Initialize embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-large-en-v1.5",
            embed_batch_size=32
        )
        
        # Create service context
        self.service_context = ServiceContext.from_defaults(
            embed_model=self.embed_model,
            chunk_size=512,
            chunk_overlap=50
        )
        
        # Create storage context
        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir=str(storage_path)
        )
        
        # Create index
        self.index = VectorStoreIndex(
            [],
            storage_context=self.storage_context,
            service_context=self.service_context
        )
    
    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to the index."""
        try:
            # Create LlamaIndex document
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
                metadata=entry.to_dict()
            )
            
            # Add to index
            self.index.insert(doc)
            
            # Persist changes
            self.index.storage_context.persist(str(self.storage_path))
            
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
            # Build metadata filter if entry types specified
            metadata_filter = None
            if entry_types:
                metadata_filter = {
                    "type": {"$in": [t.value for t in entry_types]}
                }
            
            # Create query
            vector_store_query = VectorStoreQuery(
                query_str=query,
                metadata_filter=metadata_filter,
                similarity_top_k=limit * 2  # Get extra results for score filtering
            )
            
            # Execute query
            query_result = self.index.as_query_engine(
                vector_store_query=vector_store_query
            ).query(query)
            
            # Process results
            results = []
            for node in query_result.source_nodes:
                if hasattr(node, 'score') and node.score < min_score:
                    continue
                    
                results.append({
                    "entry": MSEntry.from_dict(node.metadata),
                    "score": getattr(node, 'score', 1.0),
                    "relevance_score": getattr(node, 'relevance_score', 1.0)
                })
            
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
                if self._matches_filter(doc.metadata, metadata_filter):
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