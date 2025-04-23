"""Search functionality for MagicScroll using Redis vector store."""
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime
import logging
import os
import json
import subprocess
import numpy as np
from redis import Redis
from llama_index.core import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

from .ms_entry import MSEntry, EntryType
from .ms_types import SearchResult
from scramble.utils.logging import get_logger

if TYPE_CHECKING:
    from .ms_index import MSIndex

logger = get_logger(__name__)

class MSSearch:
    """Handles search operations across Redis."""
    
    def __init__(self, index):
        """Initialize with reference to MSIndex."""
        self.index = index
        self.container_mode = os.environ.get('REDIS_CONTAINER_MODE', '0') == '1'
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', '6379'))
        self.index_name = "magicscroll_index"
        self.vector_dim = 384  # Dimension for all-MiniLM-L6-v2 model
        
        # Get vector store from the index
        self.vector_store = self.index.store.vector_store if hasattr(self.index, 'store') else None
        self.embed_model = Settings.embed_model
        
        # Create a Redis client
        self.redis_client = Redis(host=self.redis_host, port=self.redis_port, decode_responses=True)
        
        # Verify search functionality
        self.has_search = self._check_search_module()
        
        # Log initialization
        logger.info(f"MSSearch initialized (container_mode={self.container_mode}, has_search={self.has_search})")

    def _check_search_module(self):
        """Check if Redis search module is available."""
        try:
            if self.container_mode:
                # Check using docker exec
                cmd = ["docker", "exec", "magicscroll-redis", "redis-cli", "MODULE", "LIST"]
                output = subprocess.check_output(cmd).decode('utf-8')
                return 'search' in output.lower()
            else:
                # Check using Redis client
                modules = self.redis_client.execute_command("MODULE LIST")
                if modules:
                    module_names = [m[1].decode('utf-8') if isinstance(m[1], bytes) else m[1]
                                   for m in modules if isinstance(m, list) and len(m) > 1]
                    return 'search' in module_names
                return False
        except Exception as e:
            logger.error(f"Error checking Redis search module: {e}")
            return False

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using LlamaIndex embedding model."""
        try:
            return await self.embed_model.aget_text_embedding(text)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def _vector_search(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Perform vector search in Redis."""
        try:
            if not self.has_search or not self.vector_store:
                logger.warning("Vector search not available - Redis search module not loaded")
                return []
                
            if self.container_mode:
                # Format the embedding for Redis CLI
                embedding_str = " ".join([str(x) for x in query_embedding])
                
                # Prepare the search command for Docker exec
                search_cmd = [
                    "docker", "exec", "magicscroll-redis", "redis-cli",
                    "FT.SEARCH", self.index_name,
                    "*=>[KNN", str(limit), "@embedding", "$vec", "AS", "score", "RETURN", "4", "id", "text", "doc_id", "metadata", "PARAMS", "2", "vec", embedding_str
                ]
                
                # Execute the search
                try:
                    output = subprocess.check_output(search_cmd).decode('utf-8')
                    
                    # Parse the results (simplified parsing)
                    lines = output.strip().split('\n')
                    
                    # Skip the first line (count of results)
                    results = []
                    i = 1
                    
                    while i < len(lines):
                        if lines[i].startswith(f"{self.index_name}:"):
                            doc_key = lines[i].strip()
                            doc_data = {}
                            
                            # Next lines contain field/value pairs
                            j = i + 1
                            while j < len(lines) and not lines[j].startswith(f"{self.index_name}:"):
                                if j+1 < len(lines):
                                    field, value = lines[j].strip(), lines[j+1].strip()
                                    doc_data[field] = value
                                    j += 2
                                else:
                                    j += 1
                                    
                            i = j
                            
                            # Extract document ID from the key
                            doc_id = doc_data.get('doc_id', doc_key.split(':')[-1])
                            score = float(doc_data.get('score', 0.0))
                            
                            results.append({
                                'id': doc_id,
                                'score': score,
                                'text': doc_data.get('text', ''),
                                'metadata': doc_data.get('metadata', '{}')
                            })
                        else:
                            i += 1
                            
                    return results
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error executing Redis vector search: {e}")
                    return []
            else:
                # Use LlamaIndex vector store to perform the search
                from llama_index.core.vector_stores import VectorStoreQuery
                
                query = VectorStoreQuery(
                    query_embedding=query_embedding,
                    similarity_top_k=limit
                )
                
                # Perform the query
                query_result = await self.vector_store.aquery(query)
                
                # Convert to our result format
                results = []
                for node in query_result.nodes:
                    results.append({
                        'id': node.node_id,
                        'score': node.score if hasattr(node, 'score') else 0.0,
                        'text': node.text,
                        'metadata': json.dumps(node.metadata) if hasattr(node, 'metadata') else '{}'
                    })
                    
                return results
                
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _results_to_entries(self, results: List[Dict[str, Any]]) -> List[SearchResult]:
        """Convert vector search results to MSEntry objects with search scores."""
        search_results = []
        
        for result in results:
            try:
                # Get the entry from the doc store
                entry_id = result['id']
                entry = await self.index.store.get_ms_entry(entry_id)
                
                if entry:
                    # Create a SearchResult
                    search_result = SearchResult(
                        entry=entry,
                        score=float(result['score']),
                        source='vector',  # This was a vector search
                        related_entries=[],  # No related entries for now
                        context={}  # No additional context
                    )
                    search_results.append(search_result)
                
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                
        return search_results

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Main search interface."""
        try:
            logger.info(f"Search request: query='{query}', limit={limit}")
            
            if entry_types:
                logger.info(f"Entry types filter: {[t.value for t in entry_types]}")
                
            if temporal_filter:
                start = temporal_filter.get('start', 'None')
                end = temporal_filter.get('end', 'None') 
                logger.info(f"Temporal filter: {start} to {end}")
            
            # Generate embedding for query
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate embedding for query")
                return []
            
            # Perform vector search
            results = await self._vector_search(query_embedding, limit=limit)
            
            # Convert to SearchResult objects
            search_results = await self._results_to_entries(results)
            
            # Filter by entry types if specified
            if entry_types:
                search_results = [r for r in search_results if r.entry.entry_type in entry_types]
            
            # Filter by temporal range if specified
            if temporal_filter:
                start = temporal_filter.get('start')
                end = temporal_filter.get('end')
                
                if start:
                    search_results = [r for r in search_results if r.entry.timestamp >= start]
                if end:
                    search_results = [r for r in search_results if r.entry.timestamp <= end]
            
            # Sort by score (highest first)
            search_results.sort(key=lambda x: x.score, reverse=True)
            
            # Limit results
            search_results = search_results[:limit]
            
            logger.info(f"Search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


    async def conversation_context_search(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Search optimized for finding conversation context."""
        try:
            # Log the search request
            logger.info(f"Conversation context search: '{message[:50]}...'")
            
            # Extract entities and key phrases from the message for better matching
            # For now, we'll just use the message text as-is
            
            # Use the standard search but with conversation-specific filters
            conversation_types = [EntryType.CONVERSATION]
            results = await self.search(
                query=message,
                entry_types=conversation_types,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            # We might add additional processing specific to conversation context here
            
            return results
            
        except Exception as e:
            logger.error(f"Error in conversation context search: {e}")
            return []