from redis import asyncio as aioredis
from redis.asyncio.client import Redis
from redis.asyncio.connection import ConnectionPool
from typing import Optional, Dict, Any, Union, List, Set, cast
import json
import logging
from .ms_entry import MSEntry

logger = logging.getLogger(__name__)

class RedisStore:
    """Redis storage for MagicScroll entries"""
    redis: Redis
    
    def __init__(self, namespace='magicscroll', redis_client: Optional[Redis] = None):
        """Initialize with existing client or create new one"""
        self.namespace = namespace
        self.redis = redis_client or aioredis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True
        )
        
    @classmethod
    async def create(cls, namespace='magicscroll', redis_client: Optional[Redis] = None) -> 'RedisStore':
        """Factory method for async initialization"""
        store = cls(namespace=namespace, redis_client=redis_client)
        # Test connection
        await store.redis.ping()
        return store
            
    async def store_entry(self, entry: MSEntry) -> bool:
        """Store an entry in Redis"""
        try:
            key = f"{self.namespace}:entry:{entry.id}"
            # Store entry data as dict
            entry_data = entry.to_dict()
            logger.debug(f"Storing entry in Redis: {entry_data}")
            
            # Store entry data
            await self.redis.set(key, json.dumps(entry_data))
            
            # Add to time index
            timeline_key = f"{self.namespace}:timeline"
            score = entry.created_at.timestamp()
            zadd_result = await self.redis.zadd(timeline_key, {entry.id: score})
            
            # Add type index
            type_key = f"{self.namespace}:type:{entry.entry_type.value}"
            sadd_result = await self.redis.sadd(type_key, entry.id)
            
            # Log success
            logger.info(f"Successfully stored entry {entry.id} in Redis")
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
                
            entry_data = json.loads(data)
            logger.debug(f"Retrieved entry from Redis: {entry_data}")
            return MSEntry.from_dict(entry_data)
            
        except Exception as e:
            logger.error(f"Error retrieving entry from Redis: {e}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from Redis"""
        try:
            # Get entry to determine type
            entry = await self.get_entry(entry_id)
            if not entry:
                return False
                
            # Remove entry data
            await self.redis.delete(f"{self.namespace}:entry:{entry_id}")
            
            # Remove from time index
            await self.redis.zrem(f"{self.namespace}:timeline", entry_id)
            
            # Remove from type index
            type_key = f"{self.namespace}:type:{entry.entry_type.value}"
            srem_result = await self.redis.srem(type_key, entry_id)
            
            logger.info(f"Successfully deleted entry {entry_id} from Redis")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting entry from Redis: {e}")
            return False

    async def get_entries_by_type(self, entry_type: str, limit: int = 10) -> List[MSEntry]:
        """Get entries of a specific type, ordered by timestamp"""
        try:
            # Get entry IDs from type set
            type_key = f"{self.namespace}:type:{entry_type}"
            entry_ids = cast(Set[str], await self.redis.smembers(type_key))
            
            # Get timestamps from timeline
            timeline_key = f"{self.namespace}:timeline"
            entries_with_scores = await self.redis.zrange(
                timeline_key,
                0, -1,
                withscores=True,
                desc=True
            )
            
            # Filter and sort by timestamp
            filtered_entries = [
                (entry_id, score) for entry_id, score in entries_with_scores
                if entry_id in entry_ids
            ][:limit]
            
            # Fetch full entries
            result = []
            for entry_id, _ in filtered_entries:
                entry = await self.get_entry(entry_id)
                if entry:
                    result.append(entry)
                    
            return result
            
        except Exception as e:
            logger.error(f"Error getting entries by type: {e}")
            return []