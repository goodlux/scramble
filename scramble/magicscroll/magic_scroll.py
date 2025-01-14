"""Core MagicScroll system integrating all components."""
import json
from typing import Dict, List, Any, Optional, Union, cast, TypedDict, Sequence, Mapping
from datetime import datetime, timedelta
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable
from typing_extensions import LiteralString
from functools import partial

# Local imports
from .ms_entry import MSEntry, MSConversation, EntryType
from .ms_index import MSIndexBase, LlamaIndexImpl
from .ms_store import RedisStore
from .ms_search import MSSearcher, SearchResult
from .ms_graph import MSGraphManager
from .ms_entity import EntityManager
from .chroma_client import AsyncChromaClient, ChromaCollection

# Database clients
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
import asyncio
from scramble.utils.logging import get_logger

# Config
from scramble.config import Config

logger = get_logger(__name__)

class EntityInfo(TypedDict):
    """Type information for entity data."""
    name: str
    type: str
    confidence: float
    source: str

class MagicScroll:
    """Main MagicScroll system coordinating all components."""
    
    def __init__(self):
        """Initialize components."""
        # Core services
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[aioredis.Redis] = None
        self._chroma_client: Optional[AsyncChromaClient] = None
        self.collection: Optional[ChromaCollection] = None
        
        # Component managers
        self.index: Optional[MSIndexBase] = None
        self.doc_store: Optional[RedisStore] = None
        self.graph_manager: Optional[MSGraphManager] = None
        self.entity_manager: Optional[EntityManager] = None
        self.searcher: Optional[MSSearcher] = None
        
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
            # Initialize core services
            await self._init_core_services()
            
            # Initialize component managers
            await self._init_component_managers()
            
            # Initialize Neo4j schema
            if self.graph_manager:
                await self.graph_manager.init_schema()
            
            logger.info("DigitalTrinity+ initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DigitalTrinity+: {str(e)}")
            raise RuntimeError("Failed to initialize required services")

    async def _init_core_services(self) -> None:
        """Initialize core database services."""
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

        # Initialize ChromaDB
        self._chroma_client = await AsyncChromaClient.create(
            base_url="http://localhost:8000"
        )
        
        # Test ChromaDB connection
        if await self._chroma_client.heartbeat():
            self.collection = await self._chroma_client.get_or_create_collection("magicscroll")
            logger.info("ChromaDB connection initialized")
        else:
            raise RuntimeError("Failed to connect to ChromaDB")

    async def _init_component_managers(self) -> None:
        """Initialize component managers."""
        if not all([self._neo4j_driver, self._redis_client, self._chroma_client, self.collection]):
            raise RuntimeError("Core services not initialized")

        if not isinstance(self._neo4j_driver, AsyncDriver):
            raise RuntimeError("Neo4j driver not properly initialized")
            
        self.graph_manager = MSGraphManager(self._neo4j_driver)
        self.entity_manager = EntityManager(self.graph_manager)
        self.searcher = MSSearcher(self)
        
        # Ensure chroma components are initialized
        if not isinstance(self._chroma_client, AsyncChromaClient):
            raise RuntimeError("ChromaDB client not properly initialized")
        if not isinstance(self.collection, ChromaCollection):
            raise RuntimeError("ChromaDB collection not properly initialized")
        
        # Initialize index using async create method with verified components
        chroma_client = cast(AsyncChromaClient, self._chroma_client)
        collection = cast(ChromaCollection, self.collection)
        
        self.index = await LlamaIndexImpl.create(
            chroma_client,
            collection
        )
        
        # Initialize Redis store
        if not isinstance(self._redis_client, aioredis.Redis):
            raise RuntimeError("Redis client not properly initialized")
            
        self.doc_store = RedisStore(
            namespace='magicscroll',
            redis_client=self._redis_client
        )
        
        logger.info("Component managers initialized")

    async def write_conversation(
        self,
        content: Union[str, Dict[str, Any]],
        metadata: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write a conversation entry with enhanced context and relationships."""
        try:
            if not self.index or not self.doc_store or not self.entity_manager or not self.graph_manager:
                raise RuntimeError("Required components not initialized")
                
            # Handle content format and create string version for storage
            content_str = json.dumps(content) if isinstance(content, dict) else str(content)
            temporal_metadata = content.get("temporal_context", []) if isinstance(content, dict) else []

            # Create conversation entry
            conversation = MSConversation(
                content=content_str,
                metadata={
                    "tags": metadata if metadata else [],
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "conversation",
                    "temporal_references": temporal_metadata
                },
                parent_id=parent_id
            )

            # Store in Redis first (this is fastest)
            if self.doc_store:
                await self.doc_store.store_entry(conversation)
                logger.debug(f"Stored conversation in Redis: {conversation.id}")

            # Add to Vector index
            if self.index:
                await self.index.add_entry(conversation)
                logger.debug(f"Added conversation to index: {conversation.id}")
            
            # Extract entities if available
            entities: Optional[List[str]] = None
            if self.entity_manager:
                processed_entities = await self.entity_manager.process_content(
                    content=content_str,
                    entry_id=conversation.id
                )
                if processed_entities and isinstance(processed_entities, list):
                    # Filter and convert entities to string list
                    entities = []
                    for entity in processed_entities:
                        if isinstance(entity, Mapping):
                            entity_name = entity.get("name")
                            if isinstance(entity_name, str):
                                entities.append(entity_name)
                    logger.debug(f"Extracted entities: {entities}")
            
            # Create graph relationships
            if self.graph_manager:
                # Pass both the entry object and the string content separately
                success = await self.graph_manager.create_entry_node(
                    entry=conversation,      # Pass the MSConversation object
                    content=content_str,     # Pass the string content
                    parent_id=parent_id,     # Pass parent ID for threading
                    entities=entities        # Pass extracted entities if any
                )
                if not success:
                    logger.error(f"Failed to create graph node for conversation {conversation.id}")
                else:
                    logger.debug(f"Created graph node for conversation: {conversation.id}")
            
            return conversation.id
            
        except Exception as e:
            logger.error(f"Failed to write conversation: {str(e)}")
            raise

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Enhanced search across all available systems."""
        try:
            if not self.searcher:
                return []

            # Type cast to get type checking working
            searcher = cast(MSSearcher, self.searcher)
            results = await searcher.comprehensive_search(
                query=query,
                temporal_filter=temporal_filter,
                entry_types=entry_types,
                limit=limit
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'entry': result.entry,
                    'score': result.score,
                    'source': result.source,
                    'related_entries': result.related_entries,
                    'context': result.context
                })
            
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_conversation_context(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get relevant conversation context for a message."""
        try:
            if not self.searcher:
                return []

            # Type cast to get type checking working
            searcher = cast(MSSearcher, self.searcher)
            results = await searcher.conversation_context_search(
                message=message,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'entry': result.entry,
                    'score': result.score,
                    'source': result.source,
                    'related_entries': result.related_entries,
                    'context': result.context
                })
            
            return formatted_results

        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
        

    async def _semantic_search(
        self,
        query: str,
        limit: int
    ) -> List[SearchResult]:
        """Perform semantic search using ChromaDB."""
        try:
            if not self.ms.collection:
                logger.warning("ChromaDB collection not initialized")
                return []

            # Execute query and await results
            logger.debug(f"Executing semantic search query: {query}")
            results = await self.ms.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["metadatas", "documents", "distances"]
            )
            
            search_results = []
            if results is None:
                logger.warning("No results from ChromaDB query")
                return []
                
            # Process each result
            for result in results:
                try:
                    # Handle metadata safely
                    metadata = result.get('metadata', {})
                    if isinstance(metadata, str):
                        try:
                            metadata = ast.literal_eval(metadata)
                        except:
                            metadata = {}
                            logger.warning(f"Failed to parse metadata string: {metadata}")
                    
                    # Create entry with fallbacks
                    entry = MSEntry.from_dict({
                        'id': str(result.get('id', '')),
                        'content': str(result.get('document', '')),
                        'metadata': metadata,
                        'type': metadata.get('type', 'conversation'),
                        'created_at': metadata.get('created_at', datetime.utcnow().isoformat()),
                        'updated_at': metadata.get('updated_at', datetime.utcnow().isoformat())
                    })
                    
                    # Calculate normalized score
                    distance = float(result.get('distance', 1.0))
                    score = 1.0 - min(max(distance, 0.0), 1.0)  # Ensure score is 0-1
                    
                    search_results.append(SearchResult(
                        entry=entry,
                        score=score,
                        source='semantic'
                    ))
                    logger.debug(f"Processed result for entry {entry.id} with score {score}")
                    
                except Exception as e:
                    logger.error(f"Error processing search result: {e}")
                    continue
                
            return search_results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def comprehensive_search(
        self,
        query: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Perform a comprehensive search across all available databases.
        """
        results: Dict[str, List[SearchResult]] = {
            'semantic': [],
            'graph': [],
            'temporal': [],
            'hybrid': []
        }
        
        try:
            # Semantic search via ChromaDB (primary)
            if self.ms.collection:
                semantic_results = await self._semantic_search(
                    query=query,
                    limit=limit
                )
                results['semantic'].extend(semantic_results)
                logger.debug(f"Found {len(semantic_results)} semantic results")
            
            # Graph search via Neo4j (secondary)
            if self.ms._neo4j_driver:
                graph_results = await self._graph_search(
                    search_text=query,
                    temporal_filter=temporal_filter,
                    entry_types=entry_types,
                    limit=limit
                )
                results['graph'].extend(graph_results)
                logger.debug(f"Found {len(graph_results)} graph results")
            
            # Hybrid search via LlamaIndex (if available)
            if self.ms.index:
                hybrid_results = await self._hybrid_search(
                    query=query,
                    limit=limit
                )
                results['hybrid'].extend(hybrid_results)
                logger.debug(f"Found {len(hybrid_results)} hybrid results")
            
            # Merge and rank results
            merged = await self._merge_results(results, limit)
            logger.debug(f"Merged to {len(merged)} final results")
            return merged
            
        except Exception as e:
            logger.error(f"Error in comprehensive search: {e}")
            return []

    async def _merge_results(
        self,
        results: Dict[str, List[SearchResult]],
        limit: int
    ) -> List[SearchResult]:
        """Merge and rank results from different sources."""
        merged = []
        seen_ids = set()
        
        # Scoring weights for different sources
        weights = {
            'semantic': 1.0,  # ChromaDB results get full weight
            'graph': 0.8,     # Graph results slightly lower
            'hybrid': 0.7     # Hybrid results lowest
        }
        
        # Helper to add result if not seen
        def add_result(result: SearchResult):
            if result.entry.id not in seen_ids:
                # Adjust score based on source
                result.score *= weights.get(result.source, 0.5)
                merged.append(result)
                seen_ids.add(result.entry.id)
                logger.debug(f"Added {result.source} result {result.entry.id} with score {result.score}")
        
        # Add results in priority order
        for source in ['semantic', 'graph', 'hybrid']:
            for result in results.get(source, []):
                add_result(result)
        
        # Sort by score and limit
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:limit]