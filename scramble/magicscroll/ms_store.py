from redis import asyncio as aioredis
from typing import Optional, Dict, Any, Union
import json
import logging
from .ms_entry import MSEntry

logger = logging.getLogger(__name__)

class RedisStore:
    """Redis storage for MagicScroll entries"""
    
    def __init__(self, client: Optional[aioredis.Redis] = None):
        """Initialize with existing client or create new one"""
        self.redis = client if client else aioredis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True
        )
        
    @classmethod
    async def create(cls, client: Optional[aioredis.Redis] = None) -> 'RedisStore':
        """Factory method for async initialization"""
        store = cls(client)
        # Test connection
        await store.redis.ping()
        return store
            
    async def store_entry(self, entry: MSEntry) -> bool:
        """Store an entry in Redis"""
        try:
            key = f"entry:{entry.id}"
            # Store entry data
            await self.redis.set(key, entry.json())
            # Add to time index
            await self.redis.zadd("entries:timeline", {entry.id: entry.created_at.timestamp()})
            return True
        except Exception as e:
            logger.error(f"Error storing entry in Redis: {e}")
            return False
            
    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve an entry from Redis"""
        try:
            data = await self.redis.get(f"entry:{entry_id}")
            if not data:
                return None
            return MSEntry.from_json(data)
        except Exception as e:
            logger.error(f"Error retrieving entry from Redis: {e}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from Redis"""
        try:
            # Remove entry data
            await self.redis.delete(f"entry:{entry_id}")
            # Remove from time index
            await self.redis.zrem("entries:timeline", entry_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting entry from Redis: {e}")
            return False