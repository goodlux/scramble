"""ChromaDB async client wrapper for version 0.5.23.

This module provides an async wrapper around ChromaDB operations, specifically built for:
- chromadb>=0.5.23            # Core ChromaDB package
- chromadb-client>=0.6.2      # Client interface
- httpx>=0.24.0              # Required for async HTTP operations

Required Reading:
- Client API: https://docs.trychroma.com/reference/python/client
- Collection API: https://docs.trychroma.com/reference/python/collection

Implementation Details:
- Uses httpx-based AsyncClient for ChromaDB operations to maintain LlamaIndex compatibility
- Provides async-safe embedding generation using sentence-transformers
- Handles collection operations with proper error handling and typing
- Implements robust result processing with null-safety and type checking

Example Usage:
    client = await AsyncChromaClient.create("http://localhost:8000")
    collection = await client.get_or_create_collection("mycollection")
    
    # Add documents
    await collection.add(
        embeddings=[[1.0, 2.0], [3.0, 4.0]],
        documents=["doc1", "doc2"],
        metadatas=[{"source": "web"}, {"source": "file"}],
        ids=["id1", "id2"]
    )
    
    # Query
    results = await collection.query(
        query_texts=["search text"],
        n_results=2
    )
"""

from typing import Optional, Dict, Any, List, Union, Sequence
import logging
import httpx
import chromadb
from chromadb.api.types import Collection, EmbeddingFunction, Documents, Embeddings, IDs
from chromadb.config import Settings
from chromadb.api import HttpClient
from sentence_transformers import SentenceTransformer
import torch
import asyncio
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

# Previous classes remain the same until AsyncChromaClient...

class AsyncChromaClient:
    """Async client for ChromaDB operations.
    
    Provides connection management and collection operations with proper async
    initialization and error handling. Uses httpx-based client for LlamaIndex compatibility.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the client.
        
        Args:
            base_url: ChromaDB server URL
        """
        self.base_url = base_url
        host, port = base_url.replace("http://", "").split(":")
        self._client: Optional[HttpClient] = None
        self._embedding_function: Optional[AsyncEmbeddingFunction] = None
        self.host = host
        self.port = int(port)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._client is not None and self._http_client is not None

    async def initialize(self) -> None:
        """Initialize async client and embedding function.
        
        Raises:
            RuntimeError: If initialization fails
        """
        if not self._client:
            try:
                # Initialize httpx client with appropriate timeouts
                self._http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(60.0),
                    headers={"Content-Type": "application/json"}
                )
                
                # Initialize ChromaDB client with httpx
                settings = Settings(
                    chroma_api_impl="rest",
                    chroma_server_host=self.host,
                    chroma_server_http_port=self.port,
                    chroma_client_impl="httpx"
                )
                
                self._client = HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=settings,
                    http_client=self._http_client
                )
                
                self._embedding_function = AsyncEmbeddingFunction()
                
                # Test connection
                await self._client.heartbeat()
                logger.info("ChromaDB connection established successfully")
                
            except Exception as e:
                if self._http_client:
                    await self._http_client.aclose()
                logger.error(f"Failed to initialize ChromaDB client: {e}")
                raise RuntimeError(f"ChromaDB initialization failed: {str(e)}")

    async def get_or_create_collection(self, name: str) -> ChromaCollection:
        """Get or create collection.
        
        Args:
            name: Collection name
            
        Returns:
            ChromaCollection: Wrapper around ChromaDB collection
            
        Raises:
            RuntimeError: If client not initialized or operation fails
        """
        try:
            if not self._client:
                await self.initialize()
            if not self._client:
                raise RuntimeError("ChromaDB client not initialized")
                
            collection = await self._client.get_or_create_collection(
                name=name,
                embedding_function=self._embedding_function
            )
            logger.info(f"Using collection: {name}")
            return ChromaCollection(collection)
            
        except Exception as e:
            logger.error(f"Failed to get/create collection: {str(e)}")
            raise RuntimeError(f"Collection operation failed: {str(e)}")

    @classmethod
    async def create(cls, base_url: str = "http://localhost:8000") -> 'AsyncChromaClient':
        """Factory method to create and initialize client.
        
        Args:
            base_url: ChromaDB server URL
            
        Returns:
            AsyncChromaClient: Initialized client instance
        """
        client = cls(base_url)
        await client.initialize()
        return client
        
    async def __aenter__(self) -> 'AsyncChromaClient':
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

# Rest of the file remains the same...