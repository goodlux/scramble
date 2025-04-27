"""Search functionality for MagicScroll using Milvus vector search."""
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import json
from llama_index.core import Settings

from .ms_entry import MSEntry, EntryType
from .ms_types import SearchResult
from scramble.utils.logging import get_logger

if TYPE_CHECKING:
    from .magic_scroll import MagicScroll

logger = get_logger(__name__)

class MSSearch:
    """Handles search operations with Milvus vector search."""
    
    def __init__(self, magicscroll: 'MagicScroll'):
        """Initialize with reference to MagicScroll."""
        self.magicscroll = magicscroll
        
        # Vector dimension for embedding model (all-MiniLM-L6-v2)
        self.vector_dim = 384
        
        # Load embedding model at startup
        try:
            self.embed_model = Settings.embed_model
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embed_model = None
        
        logger.info("MSSearch initialized with Milvus backend")

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using embedding model."""
        try:
            if not self.embed_model:
                logger.error("No embedding model available - search will not work!")
                return []
            
            # Generate embedding
            embedding = await self.embed_model.aget_text_embedding(text)
            
            if embedding and len(embedding) == self.vector_dim:
                return embedding
            else:
                logger.error(f"Got invalid embedding with length {len(embedding) if embedding else 0}")
                return []
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def _results_to_entries(self, results: List[Dict[str, Any]]) -> List[SearchResult]:
        """Convert vector search results to SearchResult objects."""
        search_results = []
        
        for result in results:
            try:
                # Get important information from the result
                entry_id = result.get('id', None)
                content = result.get('content', None)
                entry_type = result.get('entry_type', None)
                score = float(result.get('score', 0.5))
                created_at = result.get('created_at', datetime.utcnow().isoformat())
                metadata = result.get('metadata', {})
                
                # Try to get the full entry from the store if we have an ID
                entry = None
                if entry_id:
                    try:
                        entry = await self.magicscroll.get_ms_entry(entry_id)
                    except Exception as fetch_err:
                        logger.warning(f"Could not fetch entry {entry_id}: {fetch_err}")
                
                # If we have a full entry, use it
                if entry:
                    search_result = SearchResult(
                        entry=entry,
                        score=score,
                        source='vector',  # This was a vector search
                        related_entries=[],  # No related entries for now
                        context={}  # No additional context
                    )
                    search_results.append(search_result)
                # Otherwise create a simplified result from the available fields
                elif content and entry_type:
                    # Create a minimal entry
                    from scramble.magicscroll.ms_entry import MSEntry, EntryType
                    try:
                        # Try to parse timestamp
                        if isinstance(created_at, str):
                            timestamp = datetime.fromisoformat(created_at)
                        else:
                            timestamp = created_at
                            
                        # Try to parse metadata
                        if isinstance(metadata, str):
                            import json
                            try:
                                metadata_dict = json.loads(metadata)
                            except json.JSONDecodeError:
                                metadata_dict = {}
                        else:
                            metadata_dict = metadata
                            
                        # Create minimal entry
                        minimal_entry = MSEntry(
                            id=entry_id or str(hash(content))[-8:],  # Create a deterministic ID if none exists
                            content=content,
                            entry_type=EntryType(entry_type),
                            created_at=timestamp,
                            metadata=metadata_dict
                        )
                        
                        # Create search result
                        search_result = SearchResult(
                            entry=minimal_entry,
                            score=score,
                            source='vector',
                            related_entries=[],
                            context={}
                        )
                        search_results.append(search_result)
                        logger.info(f"Created minimal search result with score {score}")
                    except Exception as minimal_err:
                        logger.error(f"Error creating minimal entry: {minimal_err}")
                
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
            
            # If we couldn't get an embedding, return empty results
            if not query_embedding:
                logger.error("Failed to generate embedding for search query - search cannot proceed")
                # DEBUG: Add detail about the embedding model
                logger.error(f"Embedding model: {self.embed_model}")
                if hasattr(self.embed_model, 'embed_batch_size'):
                    logger.error(f"Embed batch size: {self.embed_model.embed_batch_size}")
                return []
            
            # Perform vector search using Milvus store
            results = await self.magicscroll.ms_store.search_by_vector(
                query_embedding, 
                limit=limit,
                entry_types=entry_types,
                temporal_filter=temporal_filter
            )
            
            # Convert to SearchResult objects
            search_results = await self._results_to_entries(results)
            
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
        """Search optimized for finding conversation context.
        
        This is the key function used for message enrichment - it finds relevant
        past conversations to include as context before sending to the LLM.
        """
        try:
            # Log the search request
            logger.info(f"Conversation context search: '{message[:50]}...'")
            
            # Use the standard search but with conversation-specific filters
            conversation_types = [EntryType.CONVERSATION]
            results = await self.search(
                query=message,
                entry_types=conversation_types,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            # Additional debugging for results analysis
            if results:
                logger.info(f"Conversation search returned {len(results)} results")
                for i, result in enumerate(results):
                    if hasattr(result, 'score'):
                        logger.info(f"Result {i+1} score: {result.score}")
                    if hasattr(result, 'entry') and result.entry:
                        if hasattr(result.entry, 'content'):
                            preview = result.entry.content[:100] + '...' if len(result.entry.content) > 100 else result.entry.content
                            logger.info(f"Result {i+1} preview: {preview}")
            else:
                logger.info("Conversation search returned no results")
                
                # If no results through standard path, try a direct search through Milvus
                logger.info("Attempting direct Milvus search as fallback...")
                try:
                    # Generate embedding for the query
                    query_embedding = await self._get_embedding(message)
                    if query_embedding and self.magicscroll.ms_store:
                        # Perform direct search
                        direct_results = await self.magicscroll.ms_store.search_by_vector(
                            query_embedding, 
                            limit=limit,
                            entry_types=conversation_types,
                            temporal_filter=temporal_filter
                        )
                        
                        logger.info(f"Fallback direct search returned {len(direct_results)} results")
                        
                        # Convert raw results to SearchResult objects
                        if direct_results:
                            results = await self._results_to_entries(direct_results)
                            logger.info(f"Converted {len(results)} results to SearchResult objects")
                except Exception as direct_err:
                    logger.error(f"Direct search fallback failed: {direct_err}")
            
            logger.info(f"Found {len(results)} relevant conversation contexts")
            return results
            
        except Exception as e:
            logger.error(f"Error in conversation context search: {e}")
            return []
