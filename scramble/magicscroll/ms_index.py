"""Neo4j and Redis storage implementation for MagicScroll using LlamaIndex."""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, cast
from neo4j import AsyncGraphDatabase, AsyncDriver, Query
from typing_extensions import LiteralString

# LlamaIndex core imports
from llama_index.core import Settings, Document, StorageContext
from llama_index.core.indices.property_graph import PropertyGraphIndex 
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.graph_stores.memgraph import MemgraphPropertyGraphStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.core.indices.property_graph import DynamicLLMPathExtractor
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.llms.ollama import Ollama
from llama_index.core.node_parser import SentenceSplitter 

# Local imports
from scramble.config import Config
from scramble.utils.logging import get_logger
from .ms_entry import MSEntry, EntryType
from .ms_store import MSStore
from .ms_types import SearchResult
from .ms_search import MSSearch

import asyncio
import functools

logger = get_logger(__name__)

def literal_query(text: str) -> Query:
    """Create a Query object from a string, casting to LiteralString."""
    return Query(cast(LiteralString, text))


class MSIndex:
    """LlamaIndex implementation for MagicScroll."""

    def __init__(self):
        """Initialize basic attributes."""
        self.config = Config()
        self.doc_store: Optional[MSStore] = None
        self.graph_store: Optional[MemgraphPropertyGraphStore] = None
        self.storage_context: Optional[StorageContext] = None
        self.index: Optional[PropertyGraphIndex] = None
        self.embed_model: Optional[HuggingFaceEmbedding] = None 
        self.llm: Optional[Ollama] = None
        
        Settings.node_parser = SentenceSplitter(
            chunk_size=1024,  # Increase from default 1024
            chunk_overlap=50
        )
        
    @classmethod
    async def create(cls, memgraph_url: str, auth: tuple[str, str]) -> 'MSIndex':
        """Factory method to create and initialize index."""
        instance = cls()
        
        try:
           

            
            logger.info("Configured local Ollama LLM for entity extraction")

            # # Initialize embedding model
            # instance.embed_model = HuggingFaceEmbedding(
            #     model_name="BAAI/bge-small-en-v1.5"
            # )
            
            # instance.llm = Ollama(
            #     model="granite3.1-dense:2b",  # Using granite model
            #     request_timeout=3600,
            #     temperature=0.1,
            #     HuggingFaceEmbedding=HuggingFaceEmbedding(
            #         model_name="BAAI/bge-small-en-v1.5"
            #     ) 
            # )

            # Settings.embed_model = instance.embed_model
            # Settings.llm = instance.llm
            # Initialize Neo4j property graph store


            # # Initialize redis document store before storage context and index.
            # instance.doc_store = await RedisStore.create(
            #     namespace="magicscroll"
            # )

            # # Initialize storage context with Redis docstore from our store wrapper
            # instance.storage_context = StorageContext.from_defaults(
            #     docstore=instance.doc_store.store,  # Use .store to get LlamaIndex's RedisDocumentStore
            #     property_graph_store=instance.graph_store
            # )
            
            #Define our graph extraction config
            # kg_extractor = DynamicLLMPathExtractor(
            #     llm=llm,
            #     max_triplets_per_chunk=20,
            #     allowed_entity_types=[
            #         # From our updated schema:
            #         "Message",         # Our new Message type
            #         "Conversation",    # Container for messages
            #         "Topic",          # For topic linking
            #         "Model",          # For model attribution
            #         "User"            # For user messages
            #     ],
            #     allowed_relation_types=[
            #         # Core message relationships from our schema
            #         "SENT_BY",           # Message -> User/Model
            #         "ADDRESSED_TO",      # Message -> User/Model
            #         "PART_OF",          # Message -> Conversation
            #         "NEXT_IN_SEQUENCE", # Message -> Message temporal sequence
            #         "DISCUSSES",        # Message -> Topic
            #         "REFERENCES"        # Message -> Message/Document/etc
            #     ],
            #     num_workers=4,
            # )






            # Initialize Property Graph Index with the extractor

            # Initialize direct Neo4j driver for temporal queries
            # instance.neo4j_driver = AsyncGraphDatabase.driver(
            #     neo4j_url,
            #     auth=auth
            # )
            
            # # Test Neo4j connection
            # async with instance.neo4j_driver.session() as session:
            #     await session.run(literal_query("RETURN 1"))
            
            logger.info("Initialized Memgraph Property Graph Index with Redis document store")
            return instance
            
        except Exception as e:
            logger.error(f"Error initializing MSIndex: {e}")
            raise

    def add_entry(self, entry: MSEntry) -> bool:
        """Synchronous add entry - called internally."""
        try:
                
            kg_extractor = DynamicLLMPathExtractor(
                llm=self.llm,
                max_triplets_per_chunk=20,
                num_workers=4,
                # Let the LLM infer entities and their labels (types) on the fly
                allowed_entity_types=None,
                # Let the LLM infer relationships on the fly
                allowed_relation_types=None,
                # LLM will generate any entity properties, set `None` to skip property generation (will be faster without)
                allowed_relation_props=[],
                # LLM will generate any relation properties, set `None` to skip property generation (will be faster without)
                allowed_entity_props=[],
            )
    
            self.index = PropertyGraphIndex.from_documents(
                
                documents=[],  # Initialize empty
                llm=Settings.llm,
                embed_model=self.embed_model,
                     #storage_context=instance.storage_context,
                    show_progress=True,
                    embed_kg_nodes=True,  # Enable embeddings for vector search
                use_async=True,
                property_graph_store=self.graph_store,
                kg_extractors=[kg_extractor],  # Add our configured extractor
                
            )

            modified_content = entry.content.replace("'", "\\'")
            

            doc = Document(
                doc_id=entry.id,
                text=modified_content
                
            )

            

            self.index.insert(doc)

        except Exception as e:
            logger.error(f"Error adding entry: {e}")
            return False
    
    async def aadd_entry(self, entry: MSEntry) -> bool:
        """Async wrapper around add_entry."""
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                self.add_entry,
                entry
            )
        except Exception as e:
            logger.error(f"Error in async add entry: {e}", exc_info=True)
            return False

    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get an entry from the document store."""
        try:
            if not self.storage_context:
                return None
                
            # Try docstore first
            doc = await self.storage_context.docstore.aget_document(entry_id)
            if doc and isinstance(doc.metadata, dict):
                return MSEntry.from_dict(doc.metadata)

            # Fallback to graph store
            if self.graph_store:
                nodes = await self.graph_store.aget(ids=[entry_id])
                if nodes and len(nodes) > 0:
                    return MSEntry.from_dict(nodes[0].properties)
                
            return None
                
        except Exception as e:
            logger.error(f"Error getting entry {entry_id}: {e}")
            return None


    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from both stores."""
        try:
            if not self.index or not self.storage_context:
                return False

            # Delete from property graph and document store
            self.index.delete_ref_doc(entry_id)
            
            logger.debug(f"Deleted entry {entry_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting entry {entry_id}: {e}")
            return False


    async def get_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries using temporal query."""
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


    # async def get_chain(self, entry_id: str) -> List[MSEntry]:
    #     """Get chain of entries using graph traversal."""
    #     try:
    #         if not self.neo4j_driver:
    #             return []
                
    #         # async with self.neo4j_driver.session() as session:
    #         #     result = await session.run(
    #         #         literal_query("""
    #         #         MATCH path = (start:Entry {id: $id})-[:CONTINUES*]->(end:Entry)
    #         #         UNWIND nodes(path) as n
    #         #         RETURN DISTINCT n
    #         #         ORDER BY n.created_at ASC
    #         #         """),
    #         #         {"id": entry_id}
    #         #     )
                
    #         #     entries = []
    #         #     async for record in result:
    #         #         try:
    #         #             entries.append(MSEntry.from_neo4j(record["n"]))
    #         #         except Exception as e:
    #         #             logger.error(f"Error converting node to entry: {e}")
    #         #             continue
                
    #         #     return entries
            
    #     except Exception as e:
    #         logger.error(f"Error getting entry chain for {entry_id}: {e}")
    #         return []
        

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search for entries using vector similarity and filters."""
        # Import MSSearch only when needed
        from .ms_search import MSSearch
        searcher = MSSearch(self)
        return await searcher.search(
            query=query,
            entry_types=entry_types,
            temporal_filter=temporal_filter,
            limit=limit
        )

    async def search_conversation(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Search specifically for conversation context."""
        # Import MSSearch only when needed
        from .ms_search import MSSearch
        searcher = MSSearch(self)
        return await searcher.conversation_context_search(
            message=message,
            temporal_filter=temporal_filter,
            limit=limit
        )
