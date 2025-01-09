"""Async ChromaDB client wrapper using httpx."""
from typing import Optional, Dict, Any, List
import httpx
import logging
import uuid
from uuid import uuid4

logger = logging.getLogger(__name__)

class ChromaCollection:
    """Async wrapper for ChromaDB collection operations."""
    def __init__(self, client: 'AsyncChromaClient', name: str):
        self.client = client
        self.name = name
        self._base_url = f"{client.base_url}/api/v1/collections/{name}"
        
    async def count(self) -> int:
        """Get number of items in collection."""
        try:
            response = await self.client._http_client.get(
                f"{self.client.base_url}/api/v1/collections/{self.name}"
            )
            response.raise_for_status()
            data = response.json()
            return int(data.get("count", 0))
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return 0

    async def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query the collection."""
        try:
            data = {
                "model": {
                    "name": "local",
                    "provider": "local"
                },
                "query_embeddings": query_embeddings,
                "n_results": n_results,
                "where": where or {}
            }
            
            response = await self.client._http_client.post(
                f"{self.client.base_url}/api/v1/collections/{self.name}/query",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            raise

    async def add(
        self,
        embeddings: List[List[float]],
        metadata_list: List[Dict[str, Any]],
        documents: List[str],
        ids: List[str],
        model: Optional[Dict[str, str]] = None
    ) -> None:
        """Add items to collection."""
        try:
            data = {
                "model": model or {
                    "name": "local",
                    "provider": "local"
                },
                "embeddings": embeddings,
                "metadatas": metadata_list,
                "documents": documents,
                "ids": ids
            }
            
            response = await self.client._http_client.post(
                f"{self.client.base_url}/api/v1/collections/{self.name}/add",
                json=data
            )
            response.raise_for_status()
            logger.info(f"Successfully added {len(documents)} items")
            
        except Exception as e:
            logger.error(f"Error adding to collection: {e}")
            raise

class AsyncChromaClient:
    """Async client for ChromaDB REST API."""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._http_client = httpx.AsyncClient()

    async def heartbeat(self) -> bool:
        """Check if ChromaDB is available."""
        try:
            response = await self._http_client.get(f"{self.base_url}/api/v1/heartbeat")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ChromaDB heartbeat failed: {e}")
            return False

    async def get_or_create_collection(self, name: str) -> ChromaCollection:
        """Get or create a collection."""
        try:
            # First check if collection exists
            response = await self._http_client.get(f"{self.base_url}/api/v1/collections/{name}")
            if response.status_code == 200:
                logger.info(f"Using existing collection: {name}")
                return ChromaCollection(self, name)
                
            # If not found, create it
            create_data = {
                "name": name,
                "metadata": None
            }
            response = await self._http_client.post(f"{self.base_url}/api/v1/collections", json=create_data)
            response.raise_for_status()
            logger.info(f"Created new collection: {name}")
            
            return ChromaCollection(self, name)
            
        except Exception as e:
            logger.error(f"Failed to get/create collection: {str(e)}")
            raise