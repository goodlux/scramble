"""Search functionality for MagicScroll using Neo4j and Redis."""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.indices.property_graph.retriever import PGRetriever
from llama_index.core.indices.property_graph.sub_retrievers.vector import VectorContextRetriever 
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters, FilterOperator

from .ms_entry import MSEntry, EntryType
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class SearchResult:
    """Container for search results with source and confidence information."""
    entry: MSEntry
    score: float
    source: str  # 'graph', 'temporal', 'vector', 'hybrid'
    related_entries: List[MSEntry]
    context: Dict[str, Any]

class MSSearch:
    """Handles search operations across Neo4j and Redis."""
    
    def __init__(self, magic_scroll):
        """Initialize with reference to main MagicScroll instance."""
        self.ms = magic_scroll
        
    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Main search interface combining vector and temporal search."""
        try:
            results: List[SearchResult] = []

            # Build vector retriever using LlamaIndex's async features
            if self.ms.index:
                # Build metadata filters
                metadata_filter = None
                if entry_types:
                    metadata_filter = MetadataFilters(
                        filters=[
                            MetadataFilter(
                                key="type",
                                value=[t.value for t in entry_types],
                                operator=FilterOperator.IN
                            )
                        ]
                    )

                # Create vector retriever
                vector_retriever = VectorContextRetriever(
                    graph_store=self.ms.graph_store,
                    embed_model=self.ms.index._embed_model,
                    similarity_top_k=limit,
                    include_text=True,
                    path_depth=1,  # Start with direct relationships
                    filters=metadata_filter,
                )

                # Build property graph retriever with async support 
                retriever = PGRetriever(
                    sub_retrievers=[vector_retriever],
                    use_async=True,
                    num_workers=4  # Adjust based on needs
                )

                # Create query bundle and execute async search
                query_bundle = QueryBundle(query_str=query)
                nodes = await retriever._aretrieve(query_bundle)
                
                # Convert to search results
                for node in nodes:
                    if isinstance(node, NodeWithScore) and node.metadata:
                        entry = MSEntry.from_dict(node.metadata)
                        results.append(SearchResult(
                            entry=entry,
                            score=node.score or 1.0,
                            source='hybrid',
                            related_entries=[],  # Could populate from relationships
                            context={'score': node.score}
                        ))
            
            # Add temporal context if needed
            if temporal_filter:
                temporal_results = await self._temporal_search(
                    query=query,
                    temporal_filter=temporal_filter,
                    entry_types=entry_types,
                    limit=limit
                )
                results.extend(temporal_results)

            # Sort all results by score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def conversation_context_search(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """
        Search optimized for finding conversation context.
        Uses direct graph traversal for thread finding.
        """
        try:
            if not self.ms.graph_manager:
                return []
            
            # Find related entries through graph traversal
            related = await self.ms.graph_manager.get_conversation_thread(
                entry_id=message,
                max_depth=3
            )

            if related:
                thread_result = SearchResult(
                    entry=related[0],  # Most recent message
                    score=1.0,  # Direct thread match
                    source='graph',
                    related_entries=related[1:],  # Rest of thread
                    context={'type': 'conversation_thread'}
                )
                return [thread_result]

            # Fallback to general search if no direct thread found
            return await self.search(
                query=message,
                temporal_filter=temporal_filter,
                entry_types=[EntryType.CONVERSATION],  
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error in conversation context search: {e}")
            return []

    async def _temporal_search(
        self,
        query: str,
        temporal_filter: Dict[str, datetime],
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search entries by time range using Redis."""
        try:
            if not self.ms.doc_store:
                return []
                
            # Get entries within time range
            timeline_key = f"{self.ms.doc_store.namespace}:timeline"
            start_score = temporal_filter['start'].timestamp() if 'start' in temporal_filter else "-inf"
            end_score = temporal_filter['end'].timestamp() if 'end' in temporal_filter else "+inf"
            
            # Get entries from Redis sorted set
            entry_ids = await self.ms.doc_store.redis.zrangebyscore(
                timeline_key,
                start_score,
                end_score,
                start=0,
                num=limit
            )
            
            search_results = []
            for entry_id in entry_ids:
                entry = await self.ms.doc_store.get_entry(entry_id)
                if not entry:
                    continue
                    
                # Simple content matching
                if query.lower() not in entry.content.lower():
                    continue
                    
                # Type filtering
                if entry_types and entry.entry_type not in entry_types:
                    continue
                
                # Add as search result
                search_results.append(SearchResult(
                    entry=entry,
                    score=0.5,  # Base score for temporal matches
                    source='temporal',
                    related_entries=[],
                    context={'temporal_match': True}
                ))
            
            return search_results
                
        except Exception as e:
            logger.error(f"Error in temporal search: {e}")
            return []
