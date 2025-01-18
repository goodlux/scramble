"""Search functionality for MagicScroll using Neo4j and Redis."""
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
from dataclasses import dataclass
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError
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

class MSSearcher:
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
        """Main search interface combining graph and vector similarity."""
        try:
            results: Dict[str, List[SearchResult]] = {
                'vector': [],   # Embedding-based similarity
                'graph': [],    # Graph traversal results
                'temporal': []  # Time-based results
            }
            
            # Perform vector similarity search using Neo4j embeddings
            if self.ms.index:
                vector_results = await self._vector_search(
                    query=query,
                    entry_types=entry_types,
                    limit=limit
                )
                results['vector'].extend(vector_results)
            
            # Perform graph-based search
            if self.ms.graph_manager:
                graph_results = await self._graph_search(
                    search_text=query,
                    entry_types=entry_types,
                    temporal_filter=temporal_filter,
                    limit=limit
                )
                results['graph'].extend(graph_results)
            
            # Get temporal context if needed
            if temporal_filter and self.ms.doc_store:
                temporal_results = await self._temporal_search(
                    query=query,
                    temporal_filter=temporal_filter,
                    entry_types=entry_types,
                    limit=limit
                )
                results['temporal'].extend(temporal_results)
            
            # Merge and rank results
            merged = await self._merge_results(results, limit)
            return merged
            
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
            if not self.ms.graph_manager:
                return []
                
            # First try to find direct conversation references
            cypher_query = """
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
            """
            
            async with self.ms._neo4j_driver.session() as session:
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
                    
                if search_results:
                    return search_results
            
            # If no direct matches, fall back to regular search
            return await self.search(
                query=message,
                temporal_filter=temporal_filter,
                entry_types=[EntryType.CONVERSATION],
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Error in conversation context search: {e}")
            return []

    async def _vector_search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Perform vector similarity search using Neo4j embeddings."""
        try:
            if not self.ms.index:
                return []
                
            # Get query embedding from index
            query_embedding = await self.ms.index.get_embedding(query)
            
            # Search Neo4j using vector similarity
            cypher_query = """
            CALL db.index.vector.queryNodes('document_embeddings', $k, $embedding)
            YIELD node, score
            WHERE ($types IS NULL OR node.type IN $types)
            RETURN node, score, 
                   [(node)-[:MENTIONS]->(e:Entity) | e] as entities,
                   [(node)-[:CONTINUES*1..2]-(r:Entry) | r] as related
            """
            
            async with self.ms._neo4j_driver.session() as session:
                results = await session.run(
                    cypher_query,
                    embedding=query_embedding,
                    k=limit,
                    types=[t.value for t in entry_types] if entry_types else None
                )
                
                search_results = []
                async for record in results:
                    entry = MSEntry.from_neo4j(record['node'])
                    related = [MSEntry.from_neo4j(r) for r in record['related']]
                    entities = [e['name'] for e in record['entities']]
                    
                    search_results.append(SearchResult(
                        entry=entry,
                        score=float(record['score']),
                        source='vector',
                        related_entries=related,
                        context={'entities': entities}
                    ))
                    
                return search_results
                
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []

    async def _graph_search(
        self,
        search_text: str,
        entry_types: Optional[List[EntryType]],
        temporal_filter: Optional[Dict[str, datetime]],
        limit: int
    ) -> List[SearchResult]:
        """Perform graph-based search using Neo4j."""
        try:
            if not self.ms.graph_manager:
                return []
                
            # Build type filter
            type_filter = ""
            if entry_types:
                type_filter = "AND e.type IN $types"
            
            cypher_query = f"""
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
            """
            
            async with self.ms._neo4j_driver.session() as session:
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
            'vector': 1.0,    # Embedding similarity gets highest weight
            'graph': 0.8,     # Graph connections second
            'temporal': 0.6   # Temporal matches lowest
        }
        
        # Helper to add result if not seen
        def add_result(result: SearchResult):
            if result.entry.id not in seen_ids:
                # Adjust score based on source
                result.score *= weights.get(result.source, 0.5)
                merged.append(result)
                seen_ids.add(result.entry.id)
                logger.debug(f"Added {result.source} result {result.entry.id} with score {result.score}")
        
        # Add results in priority order
        for source in ['vector', 'graph', 'temporal']:
            for result in results.get(source, []):
                add_result(result)
        
        # Sort by score and limit
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:limit]