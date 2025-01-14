"""Advanced search functionality for MagicScroll using all available databases."""
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
import re
from neo4j import AsyncGraphDatabase, AsyncDriver, Query
from neo4j.exceptions import Neo4jError
from scramble.utils.logging import get_logger
from .ms_entry import MSEntry, EntryType
from typing_extensions import LiteralString
from typing import cast

logger = get_logger(__name__)

def literal_query(text: str) -> Query:
    """Create a Query object from a string, casting to LiteralString."""
    return Query(cast(LiteralString, text))

class SearchResult:
    """Container for search results with source and confidence information."""
    def __init__(self, 
                 entry: MSEntry,
                 score: float,
                 source: str,
                 related_entries: Optional[List[MSEntry]] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.entry = entry
        self.score = score
        self.source = source  # 'semantic', 'graph', 'temporal', 'hybrid'
        self.related_entries = related_entries or []
        self.context = context or {}

class MSSearcher:
    """Handles advanced search operations across all databases."""
    
    def __init__(self, magic_scroll):
        """Initialize with reference to main MagicScroll instance."""
        self.ms = magic_scroll

    async def comprehensive_search(
        self,
        query: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Perform a comprehensive search across all available databases.
        """
        results: Dict[str, List[SearchResult]] = {
            'semantic': [],
            'graph': [],
            'temporal': [],
            'hybrid': []
        }
        
        try:
            # 1. Semantic search via ChromaDB
            if self.ms.collection:
                semantic_results = await self._semantic_search(query, limit)
                results['semantic'].extend(semantic_results)
            
            # 2. Graph-based search via Neo4j
            if self.ms._neo4j_driver:
                graph_results = await self._graph_search(
                    search_text=query,
                    temporal_filter=temporal_filter,
                    entry_types=entry_types,
                    limit=limit
                )
                results['graph'].extend(graph_results)
            
            # 3. Hybrid search via LlamaIndex
            if self.ms.index:
                hybrid_results = await self._hybrid_search(query, limit)
                results['hybrid'].extend(hybrid_results)
            
            # Merge and rank results
            merged = await self._merge_results(results, limit)
            return merged
            
        except Exception as e:
            logger.error(f"Error in comprehensive search: {e}")
            return []

    async def conversation_context_search(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """
        Search specifically for conversation context, optimized for 
        natural language queries like "remember when we talked about..."
        """
        try:
            # First, try to find direct conversation references
            if self.ms._neo4j_driver:
                async with self.ms._neo4j_driver.session() as session:
                    cypher_query = literal_query("""
                    // Find conversations that might be referenced
                    MATCH (e:Entry)
                    WHERE e.type = 'conversation'
                    AND e.content CONTAINS $search_text
                    
                    // Find conversation threads
                    OPTIONAL MATCH thread = (e)-[:CONTINUES*1..3]-(related:Entry)
                    
                    // Apply temporal filter
                    WHERE (
                        $start IS NULL OR e.created_at >= datetime($start)
                    ) AND (
                        $end IS NULL OR e.created_at <= datetime($end)
                    )
                    
                    // Return with thread context
                    RETURN e,
                           collect(DISTINCT related) as thread_entries
                    ORDER BY e.created_at DESC
                    LIMIT $limit
                    """)
                    
                    results = await session.run(
                        cypher_query,
                        search_text=message,
                        start=temporal_filter['start'].isoformat() if temporal_filter and 'start' in temporal_filter else None,
                        end=temporal_filter['end'].isoformat() if temporal_filter and 'end' in temporal_filter else None,
                        limit=limit
                    )
                    
                    search_results = []
                    async for record in results:
                        entry = MSEntry.from_neo4j(record['e'])
                        thread = [MSEntry.from_neo4j(t) for t in record['thread_entries'] if t]
                        
                        search_results.append(SearchResult(
                            entry=entry,
                            score=1.0,  # Direct conversation matches get high score
                            source='graph',
                            related_entries=thread,
                            context={'type': 'conversation_thread'}
                        ))
                        
                    return search_results
            
            # Fallback to comprehensive search if no direct matches
            return await self.comprehensive_search(message, temporal_filter, limit=limit)
            
        except Exception as e:
            logger.error(f"Error in conversation context search: {e}")
            return []

    async def _semantic_search(
        self,
        query: str,
        limit: int
    ) -> List[SearchResult]:
        """Perform semantic search using ChromaDB."""
        try:
            # Execute query and await results
            query_response = await self.ms.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["metadatas", "documents", "distances"]
            )
            
            # Safety check for expected response structure
            if not isinstance(query_response, dict):
                logger.error(f"Unexpected query response type: {type(query_response)}")
                return []
            
            # Extract components ensuring they exist
            ids = query_response.get('ids', [[]])[0]
            documents = query_response.get('documents', [[]])[0]
            metadatas = query_response.get('metadatas', [[]])[0]
            distances = query_response.get('distances', [[]])[0]
            
            # Ensure we have results
            if not ids or not documents or not metadatas or not distances:
                logger.warning("No results found in query response")
                return []
            
            search_results = []
            for i in range(len(ids)):
                try:
                    # Extract metadata safely
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    if isinstance(metadata, str):
                        try:
                            import ast
                            metadata = ast.literal_eval(metadata)
                        except:
                            metadata = {}
                    
                    # Create entry with safe defaults
                    entry = MSEntry.from_dict({
                        'id': str(ids[i]),
                        'content': str(documents[i]) if i < len(documents) else "",
                        'metadata': metadata,
                        'type': metadata.get('type', 'conversation'),
                        'created_at': metadata.get('created_at', datetime.utcnow().isoformat()),
                        'updated_at': metadata.get('updated_at', datetime.utcnow().isoformat())
                    })
                    
                    # Calculate similarity score (1 - distance)
                    distance = float(distances[i]) if i < len(distances) else 1.0
                    score = 1.0 - min(max(distance, 0.0), 1.0)  # Ensure score is 0-1
                    
                    search_results.append(SearchResult(
                        entry=entry,
                        score=score,
                        source='semantic'
                    ))
                except Exception as e:
                    logger.error(f"Error processing search result {i}: {e}")
                    continue
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def _graph_search(
        self,
        search_text: str,
        temporal_filter: Optional[Dict[str, datetime]],
        entry_types: Optional[List[EntryType]],
        limit: int
    ) -> List[SearchResult]:
        """Perform graph-based search using Neo4j."""
        try:
            if not self.ms._neo4j_driver:
                return []
                
            async with self.ms._neo4j_driver.session() as session:
                # Build type filter
                type_filter = ""
                if entry_types:
                    type_filter = "AND e.type IN $types"
                
                cypher_query = literal_query(f"""
                MATCH (e:Entry)
                WHERE e.content CONTAINS $search_text
                {type_filter}
                
                // Find related entries through entity mentions
                OPTIONAL MATCH (e)-[:MENTIONS]->(entity:Entity)
                    <-[:MENTIONS]-(related:Entry)
                
                // Apply temporal filter
                WHERE (
                    $start IS NULL OR e.created_at >= datetime($start)
                ) AND (
                    $end IS NULL OR e.created_at <= datetime($end)
                )
                
                RETURN e,
                       collect(DISTINCT entity) as entities,
                       collect(DISTINCT related) as related_entries
                LIMIT $limit
                """)
                
                results = await session.run(
                    cypher_query,
                    search_text=search_text,
                    types=[t.value for t in entry_types] if entry_types else None,
                    start=temporal_filter['start'].isoformat() if temporal_filter and 'start' in temporal_filter else None,
                    end=temporal_filter['end'].isoformat() if temporal_filter and 'end' in temporal_filter else None,
                    limit=limit
                )
                
                search_results = []
                async for record in results:
                    entry = MSEntry.from_neo4j(record['e'])
                    related = [MSEntry.from_neo4j(e) for e in record['related_entries'] if e]
                    entities = [e['name'] for e in record['entities'] if e]
                    
                    # Score based on number of connections
                    connections = len(related) + len(entities)
                    score = min(0.9, 0.5 + (connections * 0.1))
                    
                    search_results.append(SearchResult(
                        entry=entry,
                        score=score,
                        source='graph',
                        related_entries=related,
                        context={'entities': entities}
                    ))
                    
                return search_results
                
        except Exception as e:
            logger.error(f"Error in graph search: {e}")
            return []

    async def _hybrid_search(
        self,
        query: str,
        limit: int
    ) -> List[SearchResult]:
        """Perform hybrid search using LlamaIndex."""
        try:
            if not self.ms.index:
                return []
                
            results = await self.ms.index.search(
                query=query,
                limit=limit
            )
            
            return [
                SearchResult(
                    entry=result['entry'],
                    score=result.get('score', 0.5),
                    source='hybrid'
                )
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    async def _merge_results(
        self,
        results: Dict[str, List[SearchResult]],
        limit: int
    ) -> List[SearchResult]:
        """Merge and rank results from different sources."""
        merged = []
        seen_ids = set()
        
        # Scoring weights for different sources
        weights = {
            'semantic': 1.0,
            'graph': 0.8,
            'hybrid': 0.7
        }
        
        # Helper to add result if not seen
        def add_result(result: SearchResult):
            if result.entry.id not in seen_ids:
                # Adjust score based on source
                result.score *= weights.get(result.source, 0.5)
                merged.append(result)
                seen_ids.add(result.entry.id)
        
        # Add results in priority order
        for source in ['semantic', 'graph', 'hybrid']:
            for result in results.get(source, []):
                add_result(result)
        
        # Sort by score and limit
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:limit]