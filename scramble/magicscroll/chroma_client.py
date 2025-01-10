"""Async ChromaDB client wrapper."""
from typing import Optional, Dict, Any, List
import logging
from chromadb import AsyncHttpClient

logger = logging.getLogger(__name__)

class ChromaCollection:
    """Wrapper for ChromaDB collection operations."""
    def __init__(self, collection: Any):  # Use Any for now since Collection type isn't exported
        self.collection = collection
        
    async def count(self) -> int:
        """Get number of items in collection."""
        try:
            count = await self.collection.count()
            return int(count)  # Ensure we return an int
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return 0

    async def add(
        self,
        embeddings: List[List[float]],
        metadata_list: List[Dict[str, Any]],
        documents: List[str],
        ids: List[str]
    ) -> None:
        """Add items to collection."""
        try:
            # Detailed debug logging
            logger.debug("Adding to ChromaDB collection:")
            logger.debug(f"Number of items: {len(documents)}")
            logger.debug(f"Document IDs: {ids}")
            logger.debug(f"Metadata format: {metadata_list}")
            
            await self.collection.add(
                embeddings=embeddings,
                metadatas=metadata_list,
                documents=documents,
                ids=ids
            )
            logger.info(f"Successfully added {len(documents)} items")
            
        except Exception as e:
            logger.error(f"Error adding to collection: {e}")
            raise

class AsyncChromaClient:
    """Client for ChromaDB operations."""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        host, port = base_url.replace("http://", "").split(":")
        self._client: Any = None
        self.host = host
        self.port = int(port)

    async def initialize(self) -> None:
        """Initialize async client."""
        if not self._client:
            client = await AsyncHttpClient(host=self.host, port=self.port)
            self._client = client

    async def heartbeat(self) -> bool:
        """Check if ChromaDB is available."""
        try:
            if not self._client:
                await self.initialize()
            if self._client:  # Type guard
                await self._client.heartbeat()
            return True
        except Exception as e:
            logger.error(f"ChromaDB heartbeat failed: {e}")
            return False

    async def get_or_create_collection(self, _: str) -> ChromaCollection:
        """Get or create collection."""
        try:
            if not self._client:
                await self.initialize()
            if self._client:  # Type guard
                collection = await self._client.get_or_create_collection(name="magicscroll")
                logger.info("Using collection: magicscroll")
                return ChromaCollection(collection)
            raise RuntimeError("ChromaDB client not initialized")
            
        except Exception as e:
            logger.error(f"Failed to get/create collection: {str(e)}")
            raise

    @classmethod
    async def create(cls, base_url: str = "http://localhost:8000") -> 'AsyncChromaClient':
        """Factory method to create and initialize client."""
        client = cls(base_url)
        await client.initialize()
        return client