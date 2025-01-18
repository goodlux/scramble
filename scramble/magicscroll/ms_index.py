"""Neo4j and Redis storage implementation for MagicScroll using LlamaIndex."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, cast
import json
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, Query
from typing_extensions import LiteralString
from scramble.utils.logging import get_logger

# LlamaIndex core imports
from llama_index.core import (
    Settings,
    Document,
    StorageContext
)
from llama_index.core.indices.property_graph import PropertyGraphIndex 
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Local imports
from scramble.config import Config
from .ms_entry import MSEntry, EntryType

logger = get_logger(__name__)

def literal_query(text: str) -> Query:
    """Create a Query object from a string, casting to LiteralString."""
    return Query(cast(LiteralString, text))

class MSIndex:
    """LlamaIndex implementation for MagicScroll using Neo4j and Redis."""

    def __init__(self):
        """Initialize basic attributes."""
        self.config = Config()
        self.storage_path: Optional[Path] = None
        self.graph_store: Optional[Neo4jPropertyGraphStore] = None
        self.doc_store: Optional[RedisDocumentStore] = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[PropertyGraphIndex] = None
        self.neo4j_driver: Optional[AsyncDriver] = None

    @classmethod
    async def create(cls, neo4j_url: str, auth: tuple[str, str]) -> 'MSIndex':
        """Factory method to create and initialize index."""
        instance = cls()
        
        try:
            # Set up storage path for any local caching
            instance.storage_path = Path.home() / '.scramble' / 'magicscroll'
            instance.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize embedding model
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-large-en-v1.5",
                embed_batch_size=32
            )
            Settings.node_parser = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=50
            )
            Settings.llm = None  # Explicitly disable LLM usage
            
            # Initialize Redis document store
            instance.doc_store = RedisDocumentStore.from_host_and_port(
                host=instance.config.REDIS_HOST,
                port=instance.config.REDIS_PORT,
                namespace='magicscroll'
            )
            
            # Initialize Neo4j property graph store
            instance.graph_store = Neo4jPropertyGraphStore(
                url=neo4j_url,
                username=auth[0],
                password=auth[1],
                database="neo4j"  # default database
            )
            
            # Create direct Neo4j driver for raw queries if needed
            instance.neo4j_driver = AsyncGraphDatabase.driver(
                neo4j_url,
                auth=auth
            )
            
            # Test Neo4j connection
            async with instance.neo4j_driver.session() as session:
                await session.run(literal_query("RETURN 1"))
            
            # Create storage context
            instance.storage_context = StorageContext.from_defaults(
                docstore=instance.doc_store,
                property_graph_store=instance.graph_store,
                persist_dir=str(instance.storage_path)
            )
            
            # Initialize Property Graph Index with storage context
            instance.index = PropertyGraphIndex(
                storage_context=instance.storage_context,
                show_progress=True
            )
            
            logger.info("Initialized Neo4j Property Graph Index with Redis document store")
            return instance
            
        except Exception as e:
            logger.error(f"Error initializing MSIndex: {e}")
            raise

    async def add_entry(self, entry: MSEntry) -> bool:
        """Add an entry to both document store and graph index."""
        try:
            if not self.index or not self.storage_context:
                return False

            # Create LlamaIndex document with metadata
            doc = Document(
                text=entry.content,
                metadata=entry.to_dict(),
                doc_id=entry.id
            )
            
            # Store document
            self.storage_context.docstore.add_documents([doc])
            
            # Add to property graph index
            self.index.insert(doc)
            
            logger.debug(f"Added entry {entry.id} to document store and graph index")
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
        """Search using both vector similarity and graph structure."""
        try:
            if not self.index:
                return []
            
            # Build metadata filters
            metadata_filters = {}
            if entry_types:
                metadata_filters["type"] = {"$in": [t.value for t in entry_types]}
            
            # Create retriever with both vector and graph components
            retriever = self.index.as_retriever(
                similarity_top_k=limit,
                metadata_filters=metadata_filters
            )
            
            # Execute search
            response = retriever.retrieve(query)
            
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
        """Get an entry from the document store."""
        try:
            if not self.storage_context:
                return None
                
            # Get document from store
            doc = self.storage_context.docstore.get_document(entry_id)
            if not doc or not isinstance(doc.metadata, dict):
                return None
                
            return MSEntry.from_dict(doc.metadata)
                
        except Exception as e:
            logger.error(f"Error getting entry {entry_id}: {e}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from both stores."""
        try:
            if not self.index or not self.storage_context:
                return False
                
            # Delete from property graph
            self.index.delete_ref_doc(entry_id)
            
            # Delete from document store
            self.storage_context.docstore.delete_document(entry_id)
            
            logger.debug(f"Deleted entry {entry_id} from both stores")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting entry {entry_id}: {e}")
            return False

    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries using Neo4j temporal queries."""
        try:
            if not self.neo4j_driver:
                return []

            query_parts = ["MATCH (n:Entry)"]
            params: Dict[str, Any] = {}
            
            if hours is not None:
                query_parts.append("WHERE n.created_at >= datetime($cutoff)")
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                params["cutoff"] = cutoff.isoformat()
                
                if entry_types:
                    query_parts.append("AND n.type IN $types")
                    params["types"] = [t.value for t in entry_types]
            elif entry_types:
                query_parts.append("WHERE n.type IN $types")
                params["types"] = [t.value for t in entry_types]
            
            query_parts.extend([
                "RETURN n",
                "ORDER BY n.created_at DESC",
                "LIMIT $limit"
            ])
            
            params["limit"] = limit
            
            async with self.neo4j_driver.session() as session:
                result = await session.run(
                    literal_query(" ".join(query_parts)), 
                    params
                )
                
                entries = []
                async for record in result:
                    try:
                        entries.append(MSEntry.from_neo4j(record["n"]))
                    except Exception as e:
                        logger.error(f"Error converting node to entry: {e}")
                        continue
                
                return entries
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []

    async def get_chain(self, entry_id: str) -> List[MSEntry]:
        """Get chain of entries using Neo4j path queries."""
        try:
            if not self.neo4j_driver:
                return []
                
            async with self.neo4j_driver.session() as session:
                result = await session.run(
                    literal_query("""
                    MATCH path = (start:Entry {id: $id})-[:CONTINUES*]->(end:Entry)
                    UNWIND nodes(path) as n
                    RETURN DISTINCT n
                    ORDER BY n.created_at ASC
                    """),
                    {"id": entry_id}
                )
                
                entries = []
                async for record in result:
                    try:
                        entries.append(MSEntry.from_neo4j(record["n"]))
                    except Exception as e:
                        logger.error(f"Error converting node to entry: {e}")
                        continue
                
                return entries
            
        except Exception as e:
            logger.error(f"Error getting entry chain for {entry_id}: {e}")
            return []

    async def close(self):
        """Clean up resources."""
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        
        # Persist storage context if needed
        if self.storage_context:
            self.storage_context.persist(persist_dir=str(self.storage_path))