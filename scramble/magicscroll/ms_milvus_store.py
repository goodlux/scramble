"""Milvus Lite vector store implementation for MagicScroll."""
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime, timedelta
import json
import os
import hashlib
import numpy as np

from pymilvus import MilvusClient, DataType
import pymilvus
from llama_index.core import Settings

from .ms_entry import MSEntry, EntryType
from scramble.config import Config
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

# Default Milvus database file path from config
DEFAULT_DB_PATH = str(Config().get_milvus_path())

class MSMilvusStore:
    """Milvus Lite storage for MagicScroll with vector search capabilities.
    
    IMPORTANT NOTES FOR MILVUS LITE:
    1. Milvus Lite only supports FLAT index type and handles indexing automatically
    2. Keep it ultra simple - just like the example in the README
    3. No explicit index creation, no custom schema, no complex parameters
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize Milvus Lite storage."""
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_directory_exists()
        
        # Initialize Milvus connection
        try:
            # Connect to Milvus Lite with file path directly
            # For PyMilvus 2.5.7, just pass the file path directly to MilvusClient
            self.client = MilvusClient(self.db_path)
            logger.info(f"Milvus Lite store initialized at {self.db_path}")
            
            # Create or verify collections for storing entries
            self._init_collections()
            
            # Set up embedding model reference for vector operations
            self.embed_model = Settings.embed_model
            
        except Exception as e:
            logger.error(f"Error initializing Milvus Lite: {e}")
            self.client = None
            raise
    
    def _ensure_directory_exists(self):
        """Make sure the directory for the database exists."""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
    
    def _init_collections(self):
        """Initialize or verify Milvus collections."""
        try:
            # Check if conversations collection exists
            collections = self.client.list_collections()
            
            # Create conversations collection if it doesn't exist
            if "conversations" not in collections:
                logger.info("Creating 'conversations' collection")
                
                # Super simple collection creation - just like example
                self.client.create_collection(
                    collection_name="conversations",
                    dimension=384  # vector dimension
                )
                
                logger.info("Milvus collection created successfully")
            else:
                logger.info("Milvus collection 'conversations' already exists")
            
        except Exception as e:
            logger.error(f"Error initializing Milvus collections: {e}")
            raise
    
    def _str_to_int64(self, s: str) -> int:
        """Convert string UUID to int64 for Milvus primary key."""
        # Use consistent hashing to create unique numeric ID from string
        h = int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % (2**63)
        return h
    
    @classmethod
    async def create(cls, db_path: Optional[str] = None) -> 'MSMilvusStore':
        """Factory method to create store instance."""
        return cls(db_path)
    
    def _process_hit(
        self, 
        hit: Any, 
        score: float, 
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Process a hit from search results and add to results if it matches filters."""
        if not results:
            logger.warning("No results list provided to _process_hit")
            # Create a new list if one wasn't provided
            logger.warning("Creating new results list")
            results = []
        else:
            logger.debug(f"Using existing results list with {len(results)} items")
        
        # Log hit structure for debugging
        if hasattr(hit, '__dict__'):
            logger.debug(f"Processing hit with structure: {type(hit)}")
        else:
            logger.debug(f"Processing hit with structure: {type(hit)}, keys: {hit.keys() if isinstance(hit, dict) else 'Not a dict'}")
        
        # Handle different hit structures
        entity = None
        
        # Try to handle pymilvus.client.search_reasult.Hit objects
        try:
            # Access attributes directly for Hit objects
            if hasattr(hit, 'entity') and hasattr(hit, 'distance'):
                entity = hit.entity
                logger.debug(f"Found entity in Hit object: {type(entity)}")
            # Case 1: Hit has 'entity' key (direct from Milvus search as dict)
            elif isinstance(hit, dict) and 'entity' in hit:
                entity = hit['entity']
                logger.debug(f"Found entity in hit with keys: {entity.keys() if isinstance(entity, dict) else 'Not a dict'}")
            # Case 2: Hit is the entity itself
            elif isinstance(hit, dict) and 'content' in hit:
                entity = hit
                logger.debug("Hit appears to be the entity itself")
            # Handle search result that might have both id and entity in a different structure
            elif hasattr(hit, 'id') and hasattr(hit, 'distance'):
                # Get the entity if available
                if hasattr(hit, 'entity'):
                    entity = hit.entity
                else:
                    # Construct entity from hit attributes
                    entity = {
                        'id': getattr(hit, 'id', None),
                        'distance': getattr(hit, 'distance', 0.0),
                    }
                    # Try to get other possible attributes
                    for attr in ['orig_id', 'content', 'entry_type', 'created_at', 'metadata']:
                        if hasattr(hit, attr):
                            entity[attr] = getattr(hit, attr)
                logger.debug(f"Extracted entity from hit attributes: {entity}")
            else:
                logger.debug(f"Unknown hit structure, trying to process directly: {hit}")
                entity = hit
        except Exception as e:
            logger.warning(f"Error extracting entity: {e}")
            # As a last resort, try to use the entire hit as the entity
            entity = hit
        
        # Now process the entity
        if not entity:
            logger.warning("No entity found in hit")
            return results
        
        # Extract entity data, handling both dict and object-like structures
        def get_value(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            elif hasattr(obj, key):
                return getattr(obj, key, default)
            return default
        
        # Apply entry type filtering
        if entry_types:
            entry_type_value = get_value(entity, 'entry_type')
            if not entry_type_value:  # Skip if no entry type
                logger.debug(f"Skipping hit - no entry_type found")
                return results
                
            valid_types = [t.value for t in entry_types]
            if entry_type_value not in valid_types:
                logger.debug(f"Skipping hit - entry_type {entry_type_value} not in {valid_types}")
                return results
                
        # Apply temporal filtering
        if temporal_filter:
            created_at_str = get_value(entity, 'created_at')
            if not created_at_str:  # Skip if no timestamp
                logger.debug(f"Skipping hit - no created_at timestamp")
                return results
                
            try:
                created_at = datetime.fromisoformat(created_at_str)
                start = temporal_filter.get('start')
                end = temporal_filter.get('end')
                
                if start and created_at < start:
                    logger.debug(f"Skipping hit - created_at {created_at} before start {start}")
                    return results
                if end and created_at > end:
                    logger.debug(f"Skipping hit - created_at {created_at} after end {end}")
                    return results
            except ValueError:
                logger.warning(f"Invalid timestamp format in search result: {created_at_str}")
                return results
        
        # Get metadata
        metadata_str = get_value(entity, 'metadata', '{}')
        try:
            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in metadata: {metadata_str}")
            metadata = {}
        
        # Extract fields with safe defaults
        try:
            # Get ID from either orig_id or id
            entity_id = get_value(entity, 'orig_id', str(get_value(entity, 'id', '')))
            
            # Get content
            content = get_value(entity, 'content', '')
            
            # Get entry type
            entry_type = get_value(entity, 'entry_type', '')
            
            # Get created_at
            created_at_str = get_value(entity, 'created_at', datetime.now().isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                logger.warning(f"Invalid datetime format: {created_at_str}, using current time")
                created_at = datetime.now()
            
            # Create result
            result = {
                "id": entity_id,
                "score": float(score),
                "content": content,
                "entry_type": entry_type,
                "created_at": created_at,
                "metadata": metadata
            }
            
            # Add to results
            results.append(result)
            logger.debug(f"Added hit to results with score {score}, results now has {len(results)} items")
            # Log just ID and score in success message instead of full content
            logger.info(f"SUCCESSFULLY PROCESSED SEARCH RESULT: {entity_id} (score: {score:.2f})")
            # Log a brief preview of content (first 50 characters)
            content_preview = content[:50] + '...' if len(content) > 50 else content
            logger.info(f"CONTENT PREVIEW: {content_preview}")
        except Exception as e:
            logger.warning(f"Error processing hit: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
            
        # Always return the results list
        return results
    
    async def save_ms_entry(self, entry: MSEntry) -> bool:
        """Store a MagicScroll entry with vector embedding."""
        try:
            if not self.client:
                logger.warning("Cannot save entry - Milvus client not initialized")
                return False
            
            logger.info(f"Saving entry {entry.id} of type {entry.entry_type}")
            
            # Generate embedding for the entry content if we have an embedding model
            if self.embed_model:
                try:
                    embedding = await self.embed_model.aget_text_embedding(entry.content)
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")
                    embedding = None
            else:
                logger.warning("No embedding model available - entry will be stored without vector")
                embedding = None
            
            # Simple ID conversion
            int_id = int(hashlib.sha256(entry.id.encode('utf-8')).hexdigest(), 16) % (2**63)
            
            # Create simplified document structure - EXACTLY like the example
            data = [{
                "id": int_id,
                "vector": embedding,
                "orig_id": entry.id,
                "content": entry.content,
                "entry_type": entry.entry_type.value,
                "created_at": entry.created_at.isoformat(),
                "metadata": json.dumps(entry.metadata)
            }]
            
            # Simple insert without any frills
            result = self.client.insert(
                collection_name="conversations",
                data=data
            )
            
            # Debug print the insert result
            logger.info(f"Insert result: {result}")
            
            if result and result.get('insert_count', 0) > 0:
                logger.info(f"Entry {entry.id} stored successfully")
                return True
            else:
                logger.warning(f"Entry {entry.id} insert returned unexpected result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving entry: {e}")
            return False
    
    async def get_ms_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve a MagicScroll entry by ID."""
        try:
            if not self.client:
                logger.warning("Cannot retrieve entry - Milvus client not initialized")
                return None
                
            logger.info(f"Retrieving entry {entry_id}")
            
            # Convert string ID to int64 for Milvus
            int_id = self._str_to_int64(entry_id)
            
            # Query from Milvus
            results = self.client.query(
                collection_name="conversations",
                filter=f'id == {int_id}',
                output_fields=["id", "orig_id", "content", "entry_type", "created_at", "metadata"]
            )
            
            if not results or len(results) == 0:
                logger.warning(f"Entry {entry_id} not found")
                return None
                
            # Parse the row data
            row = results[0]
            metadata = json.loads(row['metadata'])
            
            # Use original string ID, not the int64 ID
            entry_id = row['orig_id']
            
            # Create MSEntry instance
            entry = MSEntry(
                id=entry_id,
                content=row['content'],
                entry_type=EntryType(row['entry_type']),
                created_at=datetime.fromisoformat(row['created_at']),
                metadata=metadata
            )
            
            logger.info(f"Successfully retrieved entry {entry_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Error retrieving entry: {e}")
            return None
    
    async def delete_ms_entry(self, entry_id: str) -> bool:
        """Delete a MagicScroll entry by ID."""
        try:
            if not self.client:
                logger.warning("Cannot delete entry - Milvus client not initialized")
                return False
                
            logger.info(f"Deleting entry {entry_id}")
            
            # Convert string ID to int64 for Milvus
            int_id = self._str_to_int64(entry_id)
            
            # Delete from Milvus
            result = self.client.delete(
                collection_name="conversations",
                filter=f'id == {int_id}'
            )
            
            if result and result.get('delete_count', 0) > 0:
                logger.info(f"Entry {entry_id} deleted successfully")
                return True
            else:
                logger.warning(f"Entry {entry_id} delete returned unexpected result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            return False
    
    async def search_by_vector(
        self, 
        query_embedding: List[float], 
        limit: int = 5,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Search entries by vector similarity with ultra-simple implementation."""
        logger.info(f"Performing vector search with {len(query_embedding)}-dimensional vector")
        logger.info(f"Search limit: {limit}")
        if entry_types:
            logger.info(f"Filtering by entry types: {[t.value for t in entry_types]}")
        if temporal_filter:
            logger.info(f"Temporal filter: {temporal_filter}")
            
        if not self.client:
            logger.warning("Cannot search - Milvus client not initialized")
            return []
            
        try:
            logger.info(f"Searching with vector, limit={limit}")
            
            # Ultra-simple search just like example
            search_results = self.client.search(
                collection_name="conversations",
                data=[query_embedding],
                limit=limit,
                output_fields=["id", "orig_id", "content", "entry_type", "created_at", "metadata"]
            )
            
            # Debug print the structure
            logger.info(f"Search results type: {type(search_results)}")
            
            # Log results in a more concise format
            if isinstance(search_results, list) and search_results:
                logger.info(f"Found {len(search_results)} result lists")
                for i, hit_list in enumerate(search_results):
                    if isinstance(hit_list, list):
                        logger.info(f"Result list {i}: {len(hit_list)} hits")
                        # Log just basic info for each hit, not the entire content
                        for j, hit in enumerate(hit_list[:3]):  # Limit to first 3 for brevity
                            if hasattr(hit, 'id') and hasattr(hit, 'distance'):
                                logger.info(f"  Hit {j}: ID={hit.id}, distance={hit.distance:.4f}")
                            elif isinstance(hit, dict) and 'id' in hit and 'distance' in hit:
                                logger.info(f"  Hit {j}: ID={hit['id']}, distance={hit['distance']:.4f}")
            elif isinstance(search_results, dict):
                logger.info(f"Search results is a dict with keys: {search_results.keys()}")
                if 'results' in search_results and isinstance(search_results['results'], list):
                    logger.info(f"Found {len(search_results['results'])} hits in results key")
            else:
                logger.info("Unknown search results structure")
            
            if not search_results:
                logger.info("Vector search returned no results (empty)")
                return []
                
            # Handle different possible structures
            if isinstance(search_results, list):
                if len(search_results) == 0:
                    logger.info("Vector search returned no results (empty list)")
                    return []
            elif isinstance(search_results, dict):
                logger.info(f"Search results is a dict with keys: {search_results.keys()}")
            
            # Process results based on actual structure
            # Create the results list
            results = []
            try:
                # Handle different possible structures
                # Approach 1: Expected structure from docs
                if isinstance(search_results, list) and len(search_results) > 0:
                    for hits in search_results:
                        if isinstance(hits, list):
                            for hit in hits:
                                # Don't log the entire hit structure - too verbose
                                logger.info(f"Processing hit: ID {hit.get('id', 'unknown')}, distance: {hit.get('distance', 'N/A')}")
                                
                                # Convert distance to score (closer distance = higher score)
                                # Milvus distances are in range [0,2], convert to [0,1] similarity scores
                                distance = hit.get('distance', 0)
                                score = 1.0 - (distance / 2.0)  # Convert distance to similarity score
                                
                                # Process the hit and update results
                                updated_results = self._process_hit(hit, score, entry_types, temporal_filter, results)
                                if updated_results:
                                    results = updated_results
                                    
                                logger.info(f"Processed hit with score {score}, results now has {len(results)} items")
                # Approach 2: Direct list of results
                elif isinstance(search_results, list):
                    for hit in search_results:
                        if isinstance(hit, dict):
                            logger.info(f"Processing direct hit: {hit}")
                            # Get score or convert from distance
                            if 'distance' in hit:
                                distance = hit.get('distance', 0)
                                score = 1.0 - (distance / 2.0)
                            else:
                                score = hit.get('score', 0.5)
                                
                            # Process the hit and update results
                            updated_results = self._process_hit(hit, score, entry_types, temporal_filter, results)
                            if updated_results:
                                results = updated_results
                                
                            logger.info(f"Processed direct hit with score {score}, results now has {len(results)} items")
                # Approach 3: Dictionary structure
                elif isinstance(search_results, dict):
                    if 'results' in search_results:
                        hits = search_results['results']
                        for hit in hits:
                            if isinstance(hit, dict):
                                logger.info(f"Processing dict hit: {hit}")
                                # Get score or convert from distance
                                if 'distance' in hit:
                                    distance = hit.get('distance', 0)
                                    score = 1.0 - (distance / 2.0)
                                else:
                                    score = hit.get('score', 0.5)
                                
                                # Process the hit and update results
                                updated_results = self._process_hit(hit, score, entry_types, temporal_filter, results)
                                if updated_results:
                                    results = updated_results
                                    
                                logger.info(f"Processed dict hit with score {score}, results now has {len(results)} items")
            except Exception as parse_err:
                logger.error(f"Error parsing search results: {parse_err}")
                
                # Check what we got so far
                logger.info(f"Final processed results count: {len(results)}")
                if len(results) == 0:
                    logger.warning("Hit processing failed - detailed debugging:")
                    # Just try to extract anything useful from the search_results
                    if isinstance(search_results, list) and len(search_results) > 0:
                        # Try a simpler approach as fallback
                        logger.info("Attempting simple extraction directly from search_results")
                        for hits in search_results:
                            if isinstance(hits, list):
                                for hit in hits:
                                    if isinstance(hit, dict) and 'entity' in hit:
                                        entity = hit['entity']
                                        results.append({
                                            "id": entity.get('orig_id', str(entity.get('id', ''))),
                                            "score": 0.5,  # Default score
                                            "content": entity.get('content', ''),
                                            "entry_type": entity.get('entry_type', ''),
                                            "created_at": entity.get('created_at', datetime.now().isoformat()),
                                            "metadata": entity.get('metadata', '{}')
                                        })
                                        logger.info(f"Added fallback result, now have {len(results)} results")
                
                # Fallback: Get entries without vector search
                if len(results) == 0:
                    logger.info("Fallback to querying without vector search")
                    try:
                        # Try to query directly without vector search
                        filter_expr = ''
                        if entry_types:
                            type_filters = [f'entry_type == "{t.value}"' for t in entry_types]
                            filter_expr = ' || '.join(type_filters)
                        
                        fallback_results = self.client.query(
                            collection_name="conversations",
                            filter=filter_expr if filter_expr else None,
                            output_fields=["id", "orig_id", "content", "entry_type", "created_at", "metadata"],
                            limit=limit
                        )
                        
                        logger.info(f"Fallback query returned {len(fallback_results)} results")
                        
                        # Process query results
                        for item in fallback_results:
                            if entry_types:
                                entry_type_value = item.get('entry_type')
                                valid_types = [t.value for t in entry_types]
                                if entry_type_value not in valid_types:
                                    continue
                                    
                            if temporal_filter:
                                created_at = datetime.fromisoformat(item.get('created_at', ''))
                                start = temporal_filter.get('start')
                                end = temporal_filter.get('end')
                                
                                if start and created_at < start:
                                    continue
                                if end and created_at > end:
                                    continue
                                    
                            results.append({
                                "id": item.get('orig_id', ''),
                                "score": 0.5,  # Default score for non-vector matches
                                "content": item.get('content', ''),
                                "entry_type": item.get('entry_type', ''),
                                "created_at": datetime.fromisoformat(item.get('created_at', datetime.now().isoformat())),
                                "metadata": json.loads(item.get('metadata', '{}'))
                            })
                    except Exception as query_err:
                        logger.error(f"Fallback query failed: {query_err}")
            
            logger.info("===========================================================")
            logger.info(f"VECTOR SEARCH COMPLETE: FOUND {len(results)} RESULTS")
            if len(results) > 0:
                logger.info("RESULTS SUMMARY:")
                # List all the result IDs and scores
                for i, result in enumerate(results[:3]):  # Show first 3 results
                    logger.info(f"  RESULT {i+1}: {result.get('id', 'N/A')} (score: {result.get('score', 0):.2f})")
                    content_preview = result.get('content', '')[:100] + '...' if len(result.get('content', '')) > 100 else result.get('content', '')
                    logger.info(f"  PREVIEW: {content_preview}")
            logger.info("SENDING RESULTS TO MESSAGE ENRICHER FOR CONTEXT BUILDING")
            logger.info("===========================================================")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    async def get_recent_entries(
        self, 
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries from the store."""
        if not self.client:
            logger.warning("Cannot get recent entries - Milvus client not initialized")
            return []
            
        try:
            logger.info(f"Getting recent entries, limit={limit}")
            
            # Build filter expression
            filter_parts = []
            
            # Add entry type filter if specified
            if entry_types:
                entry_type_values = [t.value for t in entry_types]
                if len(entry_type_values) == 1:
                    filter_parts.append(f'entry_type == "{entry_type_values[0]}"')
                else:
                    type_filters = [f'entry_type == "{t}"' for t in entry_type_values]
                    filter_parts.append(f"({' || '.join(type_filters)})")
            
            # Add time filter if specified
            if hours is not None:
                cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
                filter_parts.append(f'created_at >= "{cutoff_time}"')
            
            # Combine all filter parts
            expr = " && ".join(filter_parts) if filter_parts else ""
            
            # Query recent entries
            results = self.client.query(
                collection_name="conversations",
                filter=expr if expr else None,
                output_fields=["id", "orig_id", "content", "entry_type", "created_at", "metadata"],
                limit=limit
            )
            
            if not results:
                logger.info("No recent entries found")
                return []
            
            # Convert to MSEntry objects
            entries = []
            for row in results:
                metadata = json.loads(row['metadata'])
                
                entry = MSEntry(
                    id=row['orig_id'],  # Use original string ID
                    content=row['content'],
                    entry_type=EntryType(row['entry_type']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    metadata=metadata
                )
                entries.append(entry)
            
            logger.info(f"Retrieved {len(entries)} recent entries")
            return entries
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []
    
    async def close(self):
        """Close the Milvus connection."""
        # Milvus Lite doesn't have an explicit close method
        logger.info("Milvus Lite connection resources released")

    def __del__(self):
        """Cleanup when the object is deleted."""
        # Milvus Lite will handle cleanup automatically
        pass
