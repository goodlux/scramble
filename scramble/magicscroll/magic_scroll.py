"""Core MagicScroll system coordinating specialized components."""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from neo4j import AsyncGraphDatabase, AsyncDriver
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

# Local imports
from .ms_entry import MSEntry, MSConversation, EntryType
from .ms_search import MSSearcher, SearchResult
from .ms_store import RedisStore
from .ms_graph import MSGraphManager
from .ms_entity import EntityManager
from .ms_index import MSIndex
from scramble.utils.logging import get_logger
from scramble.config import Config

logger = get_logger(__name__)

class MagicScroll:
    """Main orchestrator for MagicScroll components."""
    
    def __init__(self):
        """Initialize component references."""
        # Core services
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[aioredis.Redis] = None
        
        # Component managers
        self.index: Optional[MSIndex] = None
        self.doc_store: Optional[RedisStore] = None
        self.graph_manager: Optional[MSGraphManager] = None
        self.entity_manager: Optional[EntityManager] = None
        self.search_manager: Optional[MSSearcher] = None
        
        # Configuration
        self.config = Config()

    @classmethod
    async def create(cls) -> 'MagicScroll':
        """Factory method to create and initialize MagicScroll."""
        magic_scroll = cls()
        await magic_scroll.initialize()
        return magic_scroll

    async def initialize(self) -> None:
        """Initialize all components."""
        try:
            # Initialize databases
            await self._init_databases()
            
            # Initialize component managers
            await self._init_managers()
            
            # Initialize Neo4j schema
            if self.graph_manager:
                await self.graph_manager.init_schema()
            
            logger.info("MagicScroll initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MagicScroll: {str(e)}")
            raise RuntimeError(f"Failed to initialize: {str(e)}")

    async def _init_databases(self) -> None:
        """Initialize database connections."""
        # Initialize Redis
        self._redis_client = aioredis.Redis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            decode_responses=True
        )
        await self._redis_client.ping()
        logger.info("Redis connection initialized")

        # Initialize Neo4j
        self._neo4j_driver = AsyncGraphDatabase.driver(
            self.config.NEO4J_URI,
            auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
        )
        async with self._neo4j_driver.session() as session:
            await session.run("RETURN 1")
        logger.info("Neo4j connection initialized")

    async def _init_managers(self) -> None:
        """Initialize component managers."""
        if not self._neo4j_driver or not self._redis_client:
            raise RuntimeError("Database connections not initialized")

        # Initialize store first (primary document storage)
        self.doc_store = RedisStore(
            namespace='magicscroll',
            redis_client=self._redis_client
        )
        
        # Initialize graph manager
        self.graph_manager = MSGraphManager(self._neo4j_driver)
        
        # Initialize entity manager
        self.entity_manager = EntityManager(self.graph_manager)
        
        # Initialize index
        self.index = await MSIndex.create(
            self.config.NEO4J_URI,
            auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
        )
        
        # Initialize search manager last (depends on other components)
        self.search_manager = MSSearcher(self)
        
        logger.info("Component managers initialized")

    async def write(
        self,
        content: Union[str, Dict[str, Any]],
        entry_type: EntryType = EntryType.CONVERSATION,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write an entry to the scroll."""
        try:
            if not self.doc_store:
                raise RuntimeError("Document store not initialized")
            if not self.index:
                raise RuntimeError("Index not initialized")
            if not self.graph_manager:
                raise RuntimeError("Graph manager not initialized")
            if not self.entity_manager:
                raise RuntimeError("Entity manager not initialized")

            # Create entry
            entry = MSEntry(
                content=content if isinstance(content, str) else str(content),
                entry_type=entry_type,
                metadata=metadata or {}
            )

            # Store in Redis (primary storage)
            stored = await self.doc_store.store_entry(entry)
            if not stored:
                raise RuntimeError("Failed to store entry in Redis")

            # Add to Neo4j index
            indexed = await self.index.add_entry(entry)
            if not indexed:
                logger.warning(f"Failed to index entry {entry.id}")

            # Extract and store entities
            if self.entity_manager:
                entities = await self.entity_manager.process_content(
                    content=entry.content,
                    entry_id=entry.id
                )
                logger.debug(f"Extracted entities for {entry.id}: {entities}")

            # Create graph relationships
            if self.graph_manager:
                success = await self.graph_manager.create_entry_node(
                    entry=entry,
                    content=entry.content,
                    parent_id=parent_id,
                    entities=entities if entities else None
                )
                if not success:
                    logger.warning(f"Failed to create graph node for {entry.id}")

            return entry.id

        except Exception as e:
            logger.error(f"Failed to write entry: {str(e)}")
            raise

    async def read(self, entry_id: str) -> Optional[MSEntry]:
        """Read an entry from the scroll."""
        try:
            if not self.doc_store:
                raise RuntimeError("Document store not initialized")
                
            # Try Redis first (fastest)
            entry = await self.doc_store.get_entry(entry_id)
            if entry:
                return entry
                
            # Fallback to Neo4j
            if self.index:
                entry = await self.index.get_entry(entry_id)
                if entry:
                    return entry
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to read entry {entry_id}: {str(e)}")
            return None

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search entries in the scroll."""
        try:
            if not self.search_manager:
                raise RuntimeError("Search manager not initialized")
                
            results = await self.search_manager.search(
                query=query,
                entry_types=entry_types,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    async def get_context(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Get conversation context for a message."""
        try:
            if not self.search_manager:
                raise RuntimeError("Search manager not initialized")
                
            results = await self.search_manager.conversation_context_search(
                message=message,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get context: {str(e)}")
            return []

    async def get_recent(
        self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries from the scroll."""
        try:
            if not self.doc_store:
                raise RuntimeError("Document store not initialized")
                
            # Use Redis store's type indexing
            if entry_types:
                entries = []
                for entry_type in entry_types:
                    type_entries = await self.doc_store.get_entries_by_type(
                        entry_type.value,
                        limit=limit
                    )
                    entries.extend(type_entries)
                
                # Sort by timestamp and limit
                entries.sort(key=lambda x: x.created_at, reverse=True)
                return entries[:limit]
            
            # If no type filter, use timeline index
            else:
                timeline_key = f"{self.doc_store.namespace}:timeline"
                entry_ids = await self.doc_store.redis.zrevrange(
                    timeline_key,
                    0,
                    limit - 1
                )
                
                entries = []
                for entry_id in entry_ids:
                    entry = await self.doc_store.get_entry(entry_id)
                    if entry:
                        entries.append(entry)
                        
                return entries
                
        except Exception as e:
            logger.error(f"Failed to get recent entries: {str(e)}")
            return []