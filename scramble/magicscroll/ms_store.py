from redis import asyncio as aioredis
from typing import Optional, Dict, Any, Union
import json
import logging
from .ms_entry import MSEntry

logger = logging.getLogger(__name__)

class RedisStore:
    """Redis storage for MagicScroll entries"""
    
    def __init__(self, namespace='magicscroll'):
        """Initialize with existing client or create new one"""
        self.namespace = namespace
        self.redis = aioredis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True
        )
        
    @classmethod
    async def create(cls, namespace='magicscroll') -> 'RedisStore':
        """Factory method for async initialization"""
        store = cls(namespace=namespace)
        # Test connection
        await store.redis.ping()
        return store
            
    async def store_entry(self, entry: MSEntry) -> bool:
        """Store an entry in Redis"""
        try:
            key = f"{self.namespace}:entry:{entry.id}"
            # Store entry data as dict
            await self.redis.set(key, json.dumps(entry.to_dict()))
            # Add to time index
            await self.redis.zadd(f"{self.namespace}:timeline", {entry.id: entry.created_at.timestamp()})
            return True
        except Exception as e:
            logger.error(f"Error storing entry in Redis: {e}")
            return False
            
    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve an entry from Redis"""
        try:
            data = await self.redis.get(f"{self.namespace}:entry:{entry_id}")
            if not data:
                return None
            return MSEntry.from_dict(json.loads(data))
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