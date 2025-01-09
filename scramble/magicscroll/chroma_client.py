"""Async ChromaDB client wrapper using httpx."""
from typing import Optional, Dict, Any, List
import httpx
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ChromaCollection:
    """Async wrapper for ChromaDB collection operations."""
    
    def __init__(self, client: 'AsyncChromaClient', name: str):
        self.client = client
        self.name = name
        self._base_url = f"{client.base_url}/api/v1/collections/{name}"
    
    async def count(self) -> int:
        """Get number of items in collection."""
        async with httpx.AsyncClient() as http:
            response = await http.get(f"{self._base_url}/count")
            return response.json()["count"]
    
    async def add(self, 
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add items to collection."""
        data = {
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": documents,
            "ids": ids
        }
        async with httpx.AsyncClient() as http:
            await http.post(f"{self._base_url}/add", json=data)
    
    async def query(self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query the collection."""
        data = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
            "where": where,
            "where_document": where_document,
            "include": include or ["metadatas", "documents", "distances"]
        }
        async with httpx.AsyncClient() as http:
            response = await http.post(f"{self._base_url}/query", json=data)
            return response.json()
    
    async def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        """Delete items from collection."""
        data = {"ids": ids, "where": where}
        async with httpx.AsyncClient() as http:
            await http.post(f"{self._base_url}/delete", json=data)
    
    async def get(self, 
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get items from collection."""
        params = {
            "ids": ids,
            "where": where,
            "limit": limit,
            "offset": offset,
            "include": include or ["metadatas", "documents"]
        }
        async with httpx.AsyncClient() as http:
            response = await http.post(f"{self._base_url}/get", json=params)
            return response.json()

class AsyncChromaClient:
    """Async client for ChromaDB REST API."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize client with connection details."""
        self.base_url = f"http://{host}:{port}"
        
    async def heartbeat(self) -> bool:
        """Check if ChromaDB is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/heartbeat")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"ChromaDB heartbeat failed: {e}")
            return False
    
    async def get_or_create_collection(self, name: str) -> ChromaCollection:
        """Get or create a collection."""
        try:
            # First try to get
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/collections/{name}")
                if response.status_code == 200:
                    return ChromaCollection(self, name)
                
            # If not found, create
            async with httpx.AsyncClient() as client:
                data = {"name": name, "metadata": None}
                await client.post(f"{self.base_url}/api/v1/collections", json=data)
                return ChromaCollection(self, name)
                
        except Exception as e:
            logger.error(f"Failed to get/create collection {name}: {e}")
            raise
    
    async def list_collections(self) -> List[str]:
        """List all collections."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/collections")
            return [c["name"] for c in response.json()]
            
    async def reset(self) -> None:
        """Reset the database."""
        async with httpx.AsyncClient() as client:
            await client.post(f"{self.base_url}/api/v1/reset")