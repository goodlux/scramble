import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, cast, Literal as TypeLiteral
from datetime import datetime, timedelta
from neo4j import AsyncGraphDatabase, AsyncDriver, Query
from neo4j.exceptions import ServiceUnavailable
from typing_extensions import LiteralString
from functools import partial

# Local imports
from .ms_entry import (
    MSEntry, 
    MSConversation, 
    MSDocument, 
    MSImage, 
    MSCode,
    EntryType
)
from .ms_index import MSIndexBase, LlamaIndexImpl
from .ms_store import RedisStore
from .chroma_client import AsyncChromaClient, ChromaCollection

# Database clients and models
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from llama_index.core import Document
import asyncio
from scramble.utils.logging import get_logger

# Config
from scramble.config import Config

logger = get_logger(__name__)

def literal_query(text: str) -> Query:
    """Create a Query object from a string, casting to LiteralString."""
    return Query(cast(LiteralString, text))

class MagicScroll:
    def __init__(self):
        """Initialize basic components."""
        # Service clients
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[aioredis.Redis] = None
        self._chroma_client: Optional[AsyncChromaClient] = None
        self._collection: Optional[ChromaCollection] = None
        
        # Core components
        self.index: Optional[MSIndexBase] = None
        self.doc_store: Optional[RedisStore] = None
        
        # Configuration
        self.config = Config()

    @classmethod
    async def create(cls) -> 'MagicScroll':
        """Factory method to create and initialize MagicScroll asynchronously."""
        magic_scroll = cls()
        
        try:
            # Initialize Redis
            magic_scroll._redis_client = aioredis.Redis(
                host=magic_scroll.config.REDIS_HOST,
                port=magic_scroll.config.REDIS_PORT,
                db=magic_scroll.config.REDIS_DB,
                decode_responses=True
            )
            await magic_scroll._redis_client.ping()
            logger.info("Redis connection initialized")

            # Initialize Neo4j
            magic_scroll._neo4j_driver = AsyncGraphDatabase.driver(
                magic_scroll.config.NEO4J_URI,
                auth=(magic_scroll.config.NEO4J_USER, magic_scroll.config.NEO4J_PASSWORD)
            )
            async with magic_scroll._neo4j_driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Neo4j connection initialized")

            # Initialize ChromaDB with async client
            magic_scroll._chroma_client = await AsyncChromaClient.create(
                base_url="http://localhost:8000"
            )
            
            # Test ChromaDB connection with retries
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if await magic_scroll._chroma_client.heartbeat():
                        magic_scroll.collection = await magic_scroll._chroma_client.get_or_create_collection("magicscroll")
                        logger.info("ChromaDB connection initialized")
                        break
                    retry_count += 1
                    logger.warning(f"ChromaDB heartbeat failed, attempt {retry_count}/{max_retries}")
                    await asyncio.sleep(1)
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"ChromaDB connection attempt {retry_count}/{max_retries} failed: {e}")
                    if retry_count >= max_retries:
                        raise RuntimeError("Failed to connect to ChromaDB after multiple attempts")
                    await asyncio.sleep(1)

            if retry_count >= max_retries:
                raise RuntimeError("Failed to connect to ChromaDB after multiple attempts")

            if not magic_scroll.collection:
                raise RuntimeError("ChromaDB collection not initialized")

            # Initialize index after core services are ready
            magic_scroll.index = await LlamaIndexImpl.create(
                chroma_client=magic_scroll._chroma_client,
                collection=magic_scroll.collection
            )
            
            # Initialize Redis store with existing client
            try:
                magic_scroll.doc_store = await RedisStore.create(
                    namespace='magicscroll',
                    redis_client=magic_scroll._redis_client
                )
                logger.info("Redis store initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis store: {e}")
                raise
            
            logger.info("Digital Trinity+ initialized successfully")
            return magic_scroll

        except Exception as e:
            logger.error(f"Failed to initialize Digital Trinity+: {str(e)}")
            raise RuntimeError("Failed to initialize required services. Ensure Docker containers are running.")

    async def write_conversation(
        self,
        content: Union[str, Dict[str, Any]],  # Allow either string or dict
        metadata: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write a conversation entry to the storage system."""
        try:
            if not self.index:
                raise RuntimeError("Index not initialized")
                
            # Handle both string and dict content formats
            if isinstance(content, dict):
                content_str = str(content)  # For index storage
                temporal_metadata = content.get("temporal_context", [])
            else:
                content_str = content
                temporal_metadata = []

            # Preserve existing metadata handling while adding temporal
            metadata_dict: Dict[str, Any] = {
                "tags": metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "conversation",
                "temporal_references": temporal_metadata  # Add temporal data
            } if metadata else {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "conversation",
                "temporal_references": temporal_metadata  # Add temporal data
            }

            # Create conversation entry
            conversation = MSConversation(
                content=content_str,
                metadata=metadata_dict,
                parent_id=parent_id
            )

            # Add to index
            success = await self.index.add_entry(conversation)
            if not success:
                raise RuntimeError("Failed to add entry to index")
            
            # Store in Redis
            redis_success = False
            if self.doc_store:
                try:
                    redis_success = await self.doc_store.store_entry(conversation)
                    if redis_success:
                        logger.info(f"Successfully stored conversation {conversation.id} in Redis")
                    else:
                        logger.warning("Failed to store conversation in Redis")
                except Exception as e:
                    logger.error(f"Error storing in Redis: {e}")

            # Store in Neo4j
            if self._neo4j_driver:
                try:
                    async with self._neo4j_driver.session() as session:
                        # Create base node
                        await session.run(
                            literal_query("""
                            CREATE (e:Entry {
                                id: $id,
                                type: 'conversation',
                                content: $content,
                                created_at: datetime($timestamp)
                            })
                            """),
                            id=conversation.id,
                            content=content_str,
                            timestamp=conversation.created_at.isoformat()
                        )
                        
                        # Add temporal metadata if present
                        if temporal_metadata:
                            await session.run(
                                literal_query("""
                                MATCH (e:Entry {id: $id})
                                SET e.temporal_references = $temporal_refs
                                """),
                                id=conversation.id,
                                temporal_refs=temporal_metadata
                            )
                        
                        # Add parent relationship if exists
                        if parent_id:
                            await session.run(
                                literal_query("""
                                MATCH (child:Entry {id: $child_id})
                                MATCH (parent:Entry {id: $parent_id})
                                CREATE (child)-[:CONTINUES]->(parent)
                                """),
                                child_id=conversation.id,
                                parent_id=parent_id
                            )
                        
                except Exception as e:
                    logger.warning(f"Failed to store in Neo4j: {e}")
            
            return conversation.id
            
        except Exception as e:
            logger.error(f"Failed to write conversation: {e}")
            raise

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[MSEntry]:
        """Enhanced search with temporal filtering support."""
        try:
            if not self.index:
                return []

            # Use Neo4j for temporal queries if available
            if self._neo4j_driver and temporal_filter:
                try:
                    async with self._neo4j_driver.session() as session:
                        # Create temporal query
                        neo4j_query = (
                            "MATCH (e:Entry) "
                            "WHERE e.created_at >= datetime($start) "
                            "AND e.created_at <= datetime($end) "
                        )
                        
                        if entry_types:
                            neo4j_query += "AND e.type IN $types "
                            
                        neo4j_query += (
                            "RETURN e "
                            "ORDER BY e.created_at DESC "
                            "LIMIT $limit"
                        )
                        
                        result = await session.run(
                            literal_query(neo4j_query),
                            start=temporal_filter.get('start', datetime.min).isoformat(),
                            end=temporal_filter.get('end', datetime.max).isoformat(),
                            types=[t.value for t in entry_types] if entry_types else None,
                            limit=limit
                        )
                        
                        entries = []
                        async for record in result:
                            node = record["e"]
                            entries.append(MSEntry(
                                content=node["content"],
                                entry_type=EntryType(node["type"]),
                                id=node["id"],
                                created_at=datetime.fromisoformat(str(node["created_at"]))
                            ))
                        return entries
                        
                except Exception as e:
                    logger.warning(f"Neo4j temporal query failed, falling back to index: {e}")

            # Fall back to index search
            results = await self.index.search(
                query=query,
                entry_types=entry_types,
                limit=limit
            )
            return [r["entry"] for r in results]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_recent(
        self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries with enhanced temporal support."""
        try:
            if hours is not None:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=hours)
                
                return await self.search(
                    query="",  # Empty query to match all
                    entry_types=entry_types,
                    temporal_filter={
                        'start': start_time,
                        'end': end_time
                    },
                    limit=limit
                )
            
            # If no hours specified, just get latest entries
            if self.index:
                return await self.index.get_recent(
                    hours=hours,
                    entry_types=entry_types,
                    limit=limit
                )
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []

    async def get_conversation_chain(
        self,
        entry_id: str,
        max_depth: int = 10
    ) -> List[MSEntry]:
        """Get the chain of conversations connected by parent_id."""
        try:
            if not self._neo4j_driver:
                # Fallback to index implementation
                if self.index:
                    return await self.index.get_chain(entry_id)
                return []

            async with self._neo4j_driver.session() as session:
                # Use Neo4j path finding to get the conversation chain
                query = (
                    f"MATCH path = (start:Entry {{id: $entry_id}}) "
                    f"-[:CONTINUES*..{max_depth}]->(end:Entry) "
                    "WHERE NOT (end)-[:CONTINUES]->() "
                    "WITH nodes(path) as entries "
                    "UNWIND entries as entry "
                    "RETURN entry "
                    "ORDER BY entry.created_at ASC"
                )
                
                result = await session.run(
                    literal_query(query),
                    entry_id=entry_id
                )
                
                entries = []
                async for record in result:
                    node = record["entry"]
                    entry = MSEntry(
                        content=node["content"],
                        entry_type=EntryType(node["type"]),
                        id=node["id"],
                        created_at=datetime.fromisoformat(str(node["created_at"]))
                    )
                    entries.append(entry)
                    
                return entries
                
        except Exception as e:
            logger.error(f"Error getting conversation chain: {e}")
            return []