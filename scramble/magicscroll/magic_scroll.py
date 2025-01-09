import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

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
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from llama_index.core import Document
import asyncio
from scramble.utils.logging import get_logger

# Config
from scramble.config import Config

logger = get_logger(__name__)

class MagicScroll:
    def __init__(self):
        """Initialize basic components."""
        # Service clients
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[aioredis.Redis] = None
        self._chroma_client: Optional[AsyncChromaClient] = None
        self.collection: Optional[ChromaCollection] = None
        
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
            magic_scroll._chroma_client = AsyncChromaClient(
                host=magic_scroll.config.CHROMA_HOST,
                port=magic_scroll.config.CHROMA_PORT
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
                    await asyncio.sleep(1)  # Wait a second before retry
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"ChromaDB connection attempt {retry_count}/{max_retries} failed: {e}")
                    if retry_count >= max_retries:
                        raise RuntimeError("Failed to connect to ChromaDB after multiple attempts")
                    await asyncio.sleep(1)

            if retry_count >= max_retries:
                raise RuntimeError("Failed to connect to ChromaDB after multiple attempts")

            # Initialize index after core services are ready
            magic_scroll.index = await LlamaIndexImpl.create()
            magic_scroll.doc_store = RedisStore(magic_scroll._redis_client)
            
            logger.info("Digital Trinity+ initialized successfully")
            return magic_scroll

        except Exception as e:
            logger.error(f"Failed to initialize Digital Trinity+: {str(e)}")
            raise RuntimeError("Failed to initialize required services. Ensure Docker containers are running.")

    async def write_conversation(self,
        content: str,
        metadata: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write a conversation entry to the storage system.
        
        Args:
            content: The conversation content
            metadata: Optional list of metadata tags
            parent_id: Optional ID of parent conversation entry
            
        Returns:
            str: The ID of the created entry
        """
        try:
            if not self.index:
                raise RuntimeError("Index not initialized")
                
            # Convert metadata list to dictionary format expected by MSConversation
            metadata_dict: Dict[str, Any] = {
                "tags": metadata
            } if metadata else {}
            
            # Create conversation entry
            conversation = MSConversation(
                content=content,
                metadata=metadata_dict,  # Now passing a dictionary
                parent_id=parent_id
            )
            
            # Add to index
            success = await self.index.add_entry(conversation)
            if not success:
                raise RuntimeError("Failed to add entry to index")
                
            # Store in Neo4j if available and there's a parent
            if self._neo4j_driver and parent_id:
                try:
                    async with self._neo4j_driver.session() as session:
                        await session.run(
                            """
                            MATCH (parent:Entry {id: $parent_id})
                            CREATE (child:Entry {
                                id: $entry_id,
                                type: 'conversation',
                                created_at: datetime()
                            })
                            CREATE (child)-[:CONTINUES]->(parent)
                            """,
                            parent_id=parent_id,
                            entry_id=conversation.id
                        )
                except Exception as e:
                    logger.warning(f"Failed to store Neo4j relationship: {e}")
            
            return conversation.id
            
        except Exception as e:
            logger.error(f"Failed to write conversation: {e}")
            raise