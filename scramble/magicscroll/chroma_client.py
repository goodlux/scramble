"""Async ChromaDB client wrapper using httpx."""
from typing import Optional, Dict, Any, List
import httpx
import logging

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
            async with httpx.AsyncClient() as http:
                # First ensure collection exists
                response = await http.get(f"{self.client.base_url}/api/v1/collections/{self.name}")
                if response.status_code == 404:
                    logger.error(f"Collection {self.name} not found")
                    return 0
                    
                # Get collection details which includes count
                if response.status_code == 200:
                    data = response.json()
                    # Check different possible response formats
                    if isinstance(data, dict):
                        # Ensure we return an integer
                        count = data.get("count", 0)
                        return int(count) if count is not None else 0
                    return 0
                    
                logger.error(f"Unexpected status code: {response.status_code}")
                return 0
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
            
    async def add(self,
        embeddings: List[List[float]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add items to collection.
        
        Args:
            embeddings: List of embeddings to add
            metadata_list: List of metadata dictionaries for each embedding
            documents: List of document texts
            ids: List of IDs for the embeddings
        """
        # ChromaDB API expects "metadatas" (their naming, not ours)
        data = {
            "embeddings": embeddings,
            "metadatas": metadata_list,  # API expects this name
            "documents": documents,
            "ids": ids
        }
        
        try:
            async with httpx.AsyncClient() as http:
                response = await http.post(f"{self._base_url}/add", json=data)
                if response.status_code != 200:
                    logger.error(f"Error adding to collection: {response.text}")
                    response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to add items to collection: {str(e)}", exc_info=True)
            raise
        

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
            async with httpx.AsyncClient() as client:
                # Try to create first
                create_data = {
                    "name": name,
                    "metadata": {"similarity_space": "cosine"}  # Changed from hnsw:space
                }
                
                try:
                    # Attempt to create first
                    response = await client.post(
                        f"{self.base_url}/api/v1/collections",
                        json=create_data
                    )
                    if response.status_code in (200, 201):
                        logger.info(f"Created new collection: {name}")
                        return ChromaCollection(self, name)
                        
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 400:  # If error isn't "already exists"
                        raise
                        
                # If creation failed, try to get existing
                response = await client.get(f"{self.base_url}/api/v1/collections/{name}")
                
                if response.status_code == 200:
                    logger.info(f"Using existing collection: {name}")
                    return ChromaCollection(self, name)
                
                # If we get here, something went wrong
                logger.error(f"Failed to get or create collection: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to get/create collection {name}: {e}")
            raise
            
        # This ensures all paths return a ChromaCollection
        raise RuntimeError(f"Failed to get or create collection: {name}")
            
    async def list_collections(self) -> List[str]:
        """List all collections."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/collections")
            if response.status_code == 200:
                collections = response.json()
                return [c["name"] for c in collections]
            return []