"""Redis store implementation for MagicScroll entries using LlamaIndex."""
from redis.asyncio.client import Redis
from typing import Optional, Dict, Any
import logging

from llama_index.core import Document
from llama_index.storage.docstore.redis import RedisDocumentStore

from .ms_entry import MSEntry

logger = logging.getLogger(__name__)

class RedisStore:
    """Redis storage for MagicScroll entries using LlamaIndex RedisDocumentStore."""
    
    def __init__(
        self,
        namespace: str = "magicscroll",
        redis_client: Optional[Redis] = None,
    ):
        """Initialize store with Redis client."""
        self.namespace = namespace
        self.store = RedisDocumentStore.from_redis_client(
            redis_client=redis_client,
            namespace=namespace
        )

    @classmethod
    async def create(
        cls,
        namespace: str = "magicscroll",
        redis_client: Optional[Redis] = None,
    ) -> 'RedisStore':
        """Factory method for async initialization."""
        store = cls(namespace=namespace, redis_client=redis_client)
        if redis_client:
            await redis_client.ping()
        return store

    async def store_entry(self, entry: MSEntry) -> bool:
        """Store a MagicScroll entry."""
        try:
            doc = entry.to_document()
            await self.store.async_add_documents([doc])
            return True
        except Exception as e:
            logger.error(f"Error storing entry: {e}")
            return False

    async def get_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve a MagicScroll entry."""
        try:
            doc = await self.store.aget_document(entry_id)
            if doc is None:
                return None
            # Cast BaseNode to Document using get_content()
            return MSEntry.from_document(Document(text=doc.get_content(), metadata=doc.metadata, doc_id=doc.id_))
        except Exception as e:
            logger.error(f"Error retrieving entry: {e}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete a MagicScroll entry."""
        try:
            await self.store.adelete_document(entry_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            return False
