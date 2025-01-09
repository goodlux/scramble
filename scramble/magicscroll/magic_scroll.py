import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

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

# Config
from scramble.config import Config

logger = logging.getLogger(__name__)

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
            
            # Test ChromaDB connection
            if await magic_scroll._chroma_client.heartbeat():
                magic_scroll.collection = await magic_scroll._chroma_client.get_or_create_collection("scroll-store")
                logger.info("ChromaDB connection initialized")
            else:
                raise RuntimeError("Failed to connect to ChromaDB")

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
        """Write a conversation to the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        entry = MSConversation(
            content=content,
            metadata={"tags": metadata} if metadata else None,
            parent_id=parent_id
        )
        
        try:
            # Store in both Redis and vector index
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
            )
            
            # Store via index
            if await self.index.add_entry(entry):
                logger.info(f"Added conversation entry {entry.id}")
                return entry.id
            else:
                raise RuntimeError("Failed to write conversation to scroll")
                
        except Exception as e:
            logger.error(f"Error writing conversation: {str(e)}")
            raise RuntimeError(f"Failed to write conversation to scroll: {str(e)}")

    async def write_document(self,
        title: str,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write a document to the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        entry = MSDocument(
            title=title,
            content=content,
            uri=uri,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added document entry {entry.id}: {title}")
            return entry.id
        else:
            raise RuntimeError("Failed to write document to scroll")
    
    async def write_image(self,
        caption: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write an image to the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        entry = MSImage(
            caption=caption,
            uri=uri,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added image entry {entry.id}")
            return entry.id
        else:
            raise RuntimeError("Failed to write image to scroll")
    
    async def write_code(self,
        code: str,
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write code to the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        entry = MSCode(
            code=code,
            language=language,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added code entry {entry.id} [{language}]")
            return entry.id
        else:
            raise RuntimeError("Failed to write code to scroll")
    
    async def remember(self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search the scroll's memory."""
        if not self.index:
            raise RuntimeError("Index not initialized")

        # Search vector index
        results = await self.index.search(query, entry_types, limit, min_score)
        
        # Fetch full entries from Redis if doc_store is available
        if self.doc_store:
            enhanced_results = []
            for result in results:
                entry_id = result["entry"].id
                full_entry = await self.doc_store.get_entry(entry_id)
                if full_entry:
                    result["entry"] = full_entry
                    enhanced_results.append(result)
            return enhanced_results
        
        return results
    
    async def recall(self, entry_id: str) -> Optional[MSEntry]:
        """Recall a specific entry from the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
        return await self.index.get_entry(entry_id)
    
    async def forget(self, entry_id: str) -> bool:
        """Remove an entry from the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
        return await self.index.delete_entry(entry_id)
    
    async def recall_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Recall recent entries from the scroll."""
        if not self.index:
            raise RuntimeError("Index not initialized")
        return await self.index.get_recent(hours, entry_types, limit)
    
    async def recall_thread(self, entry_id: str) -> List[MSEntry]:
        """Recall a complete thread of entries."""
        if not self.index:
            raise RuntimeError("Index not initialized")
        return await self.index.get_chain(entry_id)
    
    async def summarize(self) -> Dict[str, Any]:
        """Get a summary of the scroll's contents."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        recent = await self.recall_recent(hours=24)
        types = {}
        for entry in recent:
            types[entry.entry_type.value] = types.get(entry.entry_type.value, 0) + 1
            
        return {
            "recent_24h": len(recent),
            "entry_types": types,
            "latest_entry": recent[0].created_at if recent else None
        }