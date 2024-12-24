# magic_scroll.py
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
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
import redis
from llama_index.core import Document
from typing import Optional, Dict, Any

from neo4j.exceptions import ServiceUnavailable

from typing import Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
import redis.asyncio as aioredis
from chromadb import AsyncClient as ChromaAsyncClient
from .config import config
import logging


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))


logger = logging.getLogger(__name__)

    # TODO: Neo4j - Initialize graph database connection
    # TODO: Neo4j - Set up graph schema and constraints
    # TODO: Neo4j - Implement connection pooling


from pathlib import Path
from typing import Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from .config import config
import logging

logger = logging.getLogger(__name__)

class MagicScroll:
    def __init__(self):
        """Initialize basic components."""
        # Initialize connections as None - will be set up in create()
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[aioredis.Redis] = None
        self._chroma_client: Optional[ChromaAsyncClient] = None

    @classmethod
    async def create(cls) -> 'MagicScroll':
        """Factory method to create and initialize MagicScroll asynchronously."""
        magic_scroll = cls()
        
        # Initialize services if enabled
        if config.is_redis_enabled():
            await magic_scroll._init_redis()
        else:
            logger.info("Redis integration is disabled")

        if config.is_neo4j_enabled():
            await magic_scroll._init_neo4j()
        else:
            logger.info("Neo4j integration is disabled")
            
        # Initialize ChromaDB client
        await magic_scroll._init_chroma()
            
        return magic_scroll
    
    async def _init_redis(self):
        """Initialize Redis connection if enabled"""
        try:
            redis_config = config.get_redis_config()
            if redis_config:
                self._redis_client = aioredis.Redis(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    db=redis_config["db"],
                    decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("Redis connection initialized")
        except RedisConnectionError:
            logger.warning("Redis service not available - falling back to basic mode")
            self._redis_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            self._redis_client = None
            
    @property
    def has_graph(self) -> bool:
        """Check if graph capabilities are available"""
        return self._neo4j_driver is not None

    async def write_conversation(self,
        content: str,
        metadata: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write a conversation to the scroll."""
        # TODO: Neo4j - Create conversation node
        # TODO: Neo4j - Handle parent-child relationships
        # TODO: Neo4j - Add temporal relationships
        # TODO: Neo4j - Implement access control properties
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
            
            # Store in both stores via storage context
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
        """
        Write a document to the scroll.
        
        Args:
            title: Document title
            content: Document content
            uri: Where the document is stored
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
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
        """
        Write an image to the scroll.
        
        Args:
            caption: Image description
            uri: Where the image is stored
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
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
        """
        Write code to the scroll.
        
        Args:
            code: The code content
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
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
    
    async def remember(self, query: str, entry_types: Optional[List[EntryType]] = None,
                      limit: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Search the scroll's memory."""

        # TODO: Neo4j - Enhance search with graph relationships
        # TODO: Neo4j - Implement relationship-aware scoring
        # TODO: Neo4j - Add temporal path finding
        # Search vector index
        results = await self.index.search(query, entry_types, limit, min_score)
        
        # Fetch full entries from Redis
        enhanced_results = []
        for result in results:
            entry_id = result["entry"].id
            full_entry = await self.doc_store.get_entry(entry_id)
            if full_entry:
                result["entry"] = full_entry
                enhanced_results.append(result)
        
        return enhanced_results
    
    async def recall(self, entry_id: str) -> Optional[MSEntry]:
        """
        Recall a specific entry from the scroll.
        
        Args:
            entry_id: The ID of the entry to recall
            
        Returns:
            The entry if found, None otherwise
        """
        return await self.index.get_entry(entry_id)
    
    async def forget(self, entry_id: str) -> bool:
        """
        Remove an entry from the scroll.
        
        Args:
            entry_id: The ID of the entry to forget
            
        Returns:
            True if successfully forgotten
        """
        return await self.index.delete_entry(entry_id)
    
    async def recall_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """
        Recall recent entries from the scroll.
        
        Args:
            hours: Optional time window
            entry_types: Optional types to filter
            limit: Maximum number of entries
            
        Returns:
            List of recent entries
        """
        return await self.index.get_recent(hours, entry_types, limit)
    
    async def recall_thread(self, entry_id: str) -> List[MSEntry]:
        """
        Recall a complete thread of entries.
        
        Args:
            entry_id: Any entry ID in the thread
            
        Returns:
            List of entries in chronological order
        """
        return await self.index.get_chain(entry_id)
    
    async def summarize(self) -> Dict[str, Any]:
        """Get a summary of the scroll's contents."""
        recent = await self.recall_recent(hours=24)
        types = {}
        for entry in recent:
            types[entry.entry_type.value] = types.get(entry.entry_type.value, 0) + 1
            
        return {
            "recent_24h": len(recent),
            "entry_types": types,
            "latest_entry": recent[0].created_at if recent else None
        }