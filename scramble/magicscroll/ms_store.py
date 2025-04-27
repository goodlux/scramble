"""Redis storage implementation for MagicScroll using LlamaIndex."""
from typing import Optional, Dict, Any
import logging

from llama_index.core import StorageContext, Document, Settings
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.storage.index_store.redis import RedisIndexStore
from llama_index.vector_stores.redis import RedisVectorStore
from llama_index.graph_stores.memgraph import MemgraphPropertyGraphStore
from llama_index.graph_stores.memgraph import MemgraphGraphStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


from .ms_entry import MSEntry
from scramble.config import Config
from scramble.utils.logging import get_logger
from redis import Redis
logger = get_logger(__name__)

class MSStore:
    """Redis storage for MagicScroll using LlamaIndex components."""
    
    def __init__(self):
        """Initialize storage components."""
        
        try:
            # Try connecting to the Redis Stack Docker container
            logger.info("Attempting to connect to Redis...")
            
            # Read host from environment or use default
            import os
            import subprocess
            import json
            
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', '6379'))
            container_mode = os.environ.get('REDIS_CONTAINER_MODE', '0') == '1'
            namespace = 'magicscroll'
            
            # Debug connection info
            logger.info(f"Redis connection: {redis_host}:{redis_port} (container_mode={container_mode})")
            
            # Test connection and get module info
            if container_mode:
                logger.info("Using container mode for Redis operations")
                try:
                    # Use docker exec to get Redis info
                    info_cmd = ["docker", "exec", "magicscroll-redis", "redis-cli", "INFO"]
                    info_output = subprocess.check_output(info_cmd).decode('utf-8')
                    # Parse version from INFO output
                    for line in info_output.split('\n'):
                        if line.startswith('redis_version:'):
                            redis_version = line.split(':')[1].strip()
                            break
                    else:
                        redis_version = "unknown"
                    
                    logger.info(f"Connected to Redis version: {redis_version} (via container)")
                    
                    # Get module list through docker exec
                    module_cmd = ["docker", "exec", "magicscroll-redis", "redis-cli", "MODULE", "LIST"]
                    module_output = subprocess.check_output(module_cmd).decode('utf-8')
                    
                    # Parse module names from output
                    module_names = []
                    for line in module_output.split('\n'):
                        if line.strip() == 'name':
                            # Next line should be the module name
                            module_name_idx = module_output.split('\n').index(line) + 1
                            if module_name_idx < len(module_output.split('\n')):
                                module_name = module_output.split('\n')[module_name_idx].strip()
                                module_names.append(module_name)
                    
                    if 'search' in module_names:
                        logger.info(f"Redis modules found via container: {module_names}")
                        has_search_module = True
                    else:
                        logger.warning("Redis search module not found in container")
                        has_search_module = False
                        
                    # Docker exec will be used by RedisDocumentStore indirectly
                    # For now, just create a regular Redis client
                    redis_client = Redis(host=redis_host, port=redis_port, decode_responses=True)
                    
                except Exception as container_err:
                    logger.error(f"Error using Redis container: {container_err}")
                    raise
            else:
                # Standard Redis connection
                try:
                    redis_client = Redis(host=redis_host, port=redis_port, decode_responses=True, socket_connect_timeout=5.0)
                    redis_info = redis_client.info()
                    redis_version = redis_info.get('redis_version', 'unknown')
                    logger.info(f"Connected to Redis version: {redis_version}")
                    
                    # Check for modules
                    try:
                        modules = redis_client.execute_command("MODULE LIST")
                        if modules:
                            module_names = [m[1] for m in modules if isinstance(m, list) and len(m) > 1]
                            logger.info(f"Redis modules found: {module_names}")
                            has_search_module = 'search' in module_names
                        else:
                            logger.warning("No Redis modules found - vector search will not work")
                            has_search_module = False
                    except Exception as module_err:
                        logger.error(f"Error checking Redis modules: {module_err}")
                        has_search_module = False
                except Exception as redis_conn_err:
                    logger.error(f"Redis connection error: {redis_conn_err}")
                    raise
            
            # Initialize document store
            self.doc_store = RedisDocumentStore.from_host_and_port(
                host=redis_host, 
                port=redis_port,
                namespace=f"{namespace}:docs"
            )
            
            # Initialize vector store only if search module is available
            try:
                if has_search_module:
                    logger.info("Redis search module found, initializing vector store")
                    
                    # Custom vector store initialization based on connection mode
                    if container_mode:
                        logger.info("Using container-based RedisVectorStore")
                        from llama_index.vector_stores.redis import RedisVectorStore
                        from redis.commands.search.field import VectorField, TextField
                        from redis.commands.search.indexDefinition import IndexDefinition, IndexType
                        
                        # First, check if index exists
                        try:
                            # This is a workaround since we can't directly use docker exec with RedisVectorStore
                            # We'll pre-create the index if needed
                            index_name = "magicscroll_index"
                            dim = 384  # Dimension for all-MiniLM-L6-v2 model
                            
                            # Check if index exists (try to get info, will fail if doesn't exist)
                            check_cmd = ["docker", "exec", "magicscroll-redis", "redis-cli", "FT._LIST"]
                            indices = subprocess.check_output(check_cmd).decode('utf-8').split('\n')
                            
                            if index_name not in indices:
                                logger.info(f"Creating Redis vector index '{index_name}'")
                                # Create the index
                                create_cmd = [
                                    "docker", "exec", "magicscroll-redis", "redis-cli",
                                    "FT.CREATE", index_name,
                                    "ON", "HASH",
                                    "PREFIX", "1", f"{index_name}:",
                                    "SCHEMA", "text", "TEXT", 
                                    "doc_id", "TEXT",
                                    "embedding", "VECTOR", "HNSW", "6", "TYPE", "FLOAT32", "DIM", str(dim), "DISTANCE_METRIC", "COSINE"
                                ]
                                subprocess.check_output(create_cmd)
                                logger.info("Vector index created successfully")
                            else:
                                logger.info(f"Vector index '{index_name}' already exists")
                            
                            # Now use the standard RedisVectorStore
                            self.vector_store = RedisVectorStore(
                                redis_client=redis_client,
                                index_name=index_name,
                                overwrite=False  # Don't overwrite since we created it manually if needed
                            )
                            
                        except Exception as index_err:
                            logger.error(f"Error creating vector index: {index_err}")
                            raise
                    else:
                        # Regular vector store creation
                        self.vector_store = RedisVectorStore(
                            redis_client=redis_client,
                            index_name="magicscroll_index", 
                            overwrite=True
                        )
                    
                    logger.info("Vector store initialized successfully")
                else:
                    logger.warning("Redis search module not found, skipping vector store initialization")
                    self.vector_store = None
            except Exception as vector_err:
                logger.error(f"Error initializing vector store: {vector_err}")
                self.vector_store = None
            
            logger.info("Redis storage components initialized successfully")
            
        except Exception as e:
            logger.error(f"Redis initialization error: {str(e)}")
            # Continue with minimal functionality
            self.doc_store = None
            self.vector_store = None

        self.graph_store = MemgraphGraphStore(
            url= "bolt://localhost:7687",
            username="",
            password="",
        )

        self.property_graph_store = MemgraphPropertyGraphStore(
            url= "bolt://localhost:7687",
            username="",
            password=""
        )

        # Create storage context - only use components that are initialized
        storage_args = {}
        if hasattr(self, 'doc_store') and self.doc_store is not None:
            storage_args['docstore'] = self.doc_store
        if hasattr(self, 'graph_store'):
            storage_args['graph_store'] = self.graph_store
        if hasattr(self, 'property_graph_store'):
            storage_args['property_graph_store'] = self.property_graph_store
        
        self.storage_context = StorageContext.from_defaults(**storage_args)

        self.embed_model = Settings.embed_model


    @classmethod
    async def create(cls) -> 'MSStore':
        return cls()
    

    async def save_ms_entry(self, entry: MSEntry) -> bool:
        """Store a MagicScroll entry with vector embedding, using direct Redis approach."""
        try:
            # Convert to LlamaIndex document for docstore (we'll still use this part)
            doc = entry.to_document()
            
            # Generate embedding
            embedding = await self.embed_model.aget_text_embedding(doc.text)
            doc.embedding = embedding
            
            # Store in document store
            await self.doc_store.async_add_documents([doc])
            logger.info(f"Entry {entry.id} stored to redis docstore")
            
            # DIRECT APPROACH: Skip LlamaIndex vector store and use Redis directly
            try:
                # Format the embedding for Redis CLI
                embedding_str = " ".join([str(x) for x in embedding])
                
                # Create Redis hash with vector embedding
                import subprocess
                import json
                
                # Prepare metadata
                metadata_json = json.dumps(doc.metadata)
                
                # Construct Redis key
                redis_key = f"magicscroll_index:{doc.doc_id}"
                
                # Prepare HSET command
                hset_cmd = [
                    "docker", "exec", "magicscroll-redis", "redis-cli",
                    "HSET", redis_key,
                    "text", doc.text,
                    "doc_id", doc.doc_id,
                    "metadata", metadata_json,
                    "embedding", embedding_str
                ]
                
                # Execute command
                subprocess.check_output(hset_cmd)
                logger.info(f"✅ Entry {entry.id} stored directly to Redis with vector embedding")
                    
            except Exception as vector_err:
                logger.error(f"Error storing entry with vector: {vector_err}")
                # Continue despite vector store error
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing entry: {e}", exc_info=True)
            return False


    async def get_ms_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve a MagicScroll entry."""
        try:
            stored_doc = await self.doc_store.aget_document(entry_id)  
            if stored_doc is None:
                return None
                
            # Convert while preserving MSEntry's original ID
            doc = Document(
                text=stored_doc.get_content(),
                metadata=stored_doc.metadata,
                doc_id=entry_id,  
                embedding=stored_doc.embedding,
            )

            return MSEntry.from_document(doc)
        except Exception as e:
            logger.error(f"Error retrieving entry: {e}")
            return None


    async def delete_ms_entry(self, entry_id: str) -> bool:
        """Delete a MagicScroll entry using direct Redis approach."""
        try:
            # Delete from document store
            await self.doc_store.adelete_document(entry_id)
            
            # DIRECT APPROACH: Delete from Redis vector store directly
            try:
                # Construct Redis key
                redis_key = f"magicscroll_index:{entry_id}"
                
                # Prepare DEL command
                import subprocess
                del_cmd = [
                    "docker", "exec", "magicscroll-redis", "redis-cli",
                    "DEL", redis_key
                ]
                
                # Execute command
                subprocess.check_output(del_cmd)
                logger.info(f"Entry {entry_id} deleted from vector store directly")
            except Exception as vector_err:
                logger.error(f"Error deleting entry from vector store: {vector_err}")
                # Continue despite vector store error
                
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            return False