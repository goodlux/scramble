"""Redis store implementation for MagicScroll entries."""
from redis import asyncio as aioredis
from redis.asyncio.client import Redis
from typing import Optional, Dict, Any, List, Set, cast
import json
import logging
from datetime import datetime

from llama_index.core import Document
from llama_index.core.schema import BaseNode
from llama_index.core.storage.docstore import BaseDocumentStore

from .ms_entry import MSEntry, EntryType

logger = logging.getLogger(__name__)

class RedisStore(BaseDocumentStore):
    """Redis storage for MagicScroll entries."""
    
    def __init__(
        self,
        namespace: str = "magicscroll",
        redis_client: Optional[Redis] = None,
        redis_kwargs: Optional[Dict[str, Any]] = None
    ):
        """Initialize store with Redis client."""
        super().__init__()
        self.namespace = namespace
        redis_kwargs = redis_kwargs or {
            "host": "localhost",
            "port": 6379,
            "decode_responses": True
        }
        self.redis = redis_client or aioredis.Redis(**redis_kwargs)

    @classmethod
    async def create(
        cls,
        namespace: str = "magicscroll",
        redis_client: Optional[Redis] = None,
        **redis_kwargs
    ) -> 'RedisStore':
        """Factory method for async initialization."""
        store = cls(namespace=namespace, redis_client=redis_client, redis_kwargs=redis_kwargs)
        await store.redis.ping()  # Test connection
        return store

    def _get_key(self, entry_id: str) -> str:
        """Get Redis key for entry data."""
        return f"{self.namespace}:entry:{entry_id}"

    def _get_timeline_key(self) -> str:
        """Get Redis key for timeline index."""
        return f"{self.namespace}:timeline"

    def _get_type_key(self, entry_type: str) -> str:
        """Get Redis key for type index."""
        return f"{self.namespace}:type:{entry_type}"

    # Public API - Uses entry terminology
    async def add_entries(
        self,
        entries: List[MSEntry],
        allow_update: bool = True
    ) -> None:
        """Add entries to store."""
        documents = [entry.to_document() for entry in entries]
        await self._add_documents(documents, allow_update)

    async def get_entry(
        self,
        entry_id: str,
        raise_error: bool = True
    ) -> Optional[MSEntry]:
        """Get entry by ID."""
        doc = await self._get_document(entry_id, raise_error)
        if doc is None:
            return None
        return MSEntry.from_document(doc)

    async def delete_entry(
        self,
        entry_id: str,
        raise_error: bool = True
    ) -> None:
        """Delete entry by ID."""
        await self._delete_document(entry_id, raise_error)

    async def get_all_entries(self) -> List[MSEntry]:
        """Get all entries ordered by timestamp."""
        docs = await self._get_all_documents()
        return [MSEntry.from_document(doc) for doc in docs]

    async def get_entries_by_type(
        self,
        entry_type: str,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get entries of specific type, ordered by timestamp."""
        docs = await self._get_documents_by_type(entry_type, limit)
        return [MSEntry.from_document(doc) for doc in docs]

    # LlamaIndex interface implementation - Uses document terminology
    async def add_documents(
        self,
        docs: List[Document],
        allow_update: bool = True
    ) -> None:
        """LlamaIndex interface method - internally calls _add_documents."""
        await self._add_documents(docs, allow_update)

    async def get_document(
        self,
        doc_id: str,
        raise_error: bool = True
    ) -> Optional[Document]:
        """LlamaIndex interface method - internally calls _get_document."""
        return await self._get_document(doc_id, raise_error)

    async def delete_document(
        self,
        doc_id: str,
        raise_error: bool = True
    ) -> None:
        """LlamaIndex interface method - internally calls _delete_document."""
        await self._delete_document(doc_id, raise_error)

    # Private implementation - Uses document terminology to match LlamaIndex
    async def _add_documents(
        self,
        docs: List[Document],
        allow_update: bool = True
    ) -> None:
        """Internal method to add documents to store."""
        try:
            for doc in docs:
                # Store document data
                key = self._get_key(doc.doc_id)
                doc_data = {
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "metadata": doc.metadata
                }
                await self.redis.set(key, json.dumps(doc_data))

                # Add to timeline index using created_at from metadata
                created_at = doc.metadata.get("created_at")
                if created_at:
                    try:
                        timestamp = datetime.fromisoformat(created_at).timestamp()
                        await self.redis.zadd(
                            self._get_timeline_key(),
                            {doc.doc_id: timestamp}
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid created_at timestamp for {doc.doc_id}: {e}")

                # Add to type index if type is in metadata
                doc_type = doc.metadata.get("type")
                if doc_type:
                    await self.redis.sadd(
                        self._get_type_key(doc_type),
                        doc.doc_id
                    )

        except Exception as e:
            logger.error(f"Error adding documents to Redis: {e}")
            raise

    async def _get_document(
        self,
        doc_id: str,
        raise_error: bool = True
    ) -> Optional[Document]:
        """Internal method to get document by ID."""
        try:
            data = await self.redis.get(self._get_key(doc_id))
            if not data:
                if raise_error:
                    raise ValueError(f"Document not found: {doc_id}")
                return None

            doc_data = json.loads(data)
            return Document(
                text=doc_data["text"],
                doc_id=doc_data["doc_id"],
                metadata=doc_data.get("metadata", {})
            )

        except Exception as e:
            logger.error(f"Error retrieving document from Redis: {e}")
            if raise_error:
                raise
            return None

    async def _delete_document(
        self,
        doc_id: str,
        raise_error: bool = True
    ) -> None:
        """Internal method to delete document by ID."""
        try:
            # Get document to check type before deletion
            doc = await self._get_document(doc_id, raise_error=raise_error)
            if not doc:
                return

            # Remove from main storage
            await self.redis.delete(self._get_key(doc_id))

            # Remove from timeline
            await self.redis.zrem(self._get_timeline_key(), doc_id)

            # Remove from type index
            doc_type = doc.metadata.get("type")
            if doc_type:
                await self.redis.srem(self._get_type_key(doc_type), doc_id)

        except Exception as e:
            logger.error(f"Error deleting document from Redis: {e}")
            if raise_error:
                raise

    async def _get_all_documents(self) -> List[Document]:
        """Internal method to get all documents."""
        try:
            # Get all document IDs from timeline, ordered by timestamp
            doc_ids = await self.redis.zrange(self._get_timeline_key(), 0, -1)
            
            # Fetch all documents
            documents = []
            for doc_id in doc_ids:
                doc = await self._get_document(doc_id, raise_error=False)
                if doc is not None:
                    documents.append(doc)
            
            return documents

        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            return []

    async def _get_documents_by_type(
        self,
        entry_type: str,
        limit: int = 10
    ) -> List[Document]:
        """Internal method to get documents by type."""
        try:
            # Get document IDs of specified type
            doc_ids = cast(
                Set[str],
                await self.redis.smembers(self._get_type_key(entry_type))
            )

            if not doc_ids:
                return []

            # Get timestamps from timeline
            timeline_scores = await self.redis.zrange(
                self._get_timeline_key(),
                0, -1,
                withscores=True,
                desc=True
            )

            # Filter by type and limit
            matching_ids = [
                doc_id for doc_id, _ in timeline_scores
                if doc_id in doc_ids
            ][:limit]

            # Fetch documents
            documents = []
            for doc_id in matching_ids:
                doc = await self._get_document(doc_id, raise_error=False)
                if doc is not None:
                    documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error getting documents by type: {e}")
            return []