#!/usr/bin/env python3
"""
Custom Milvus index creation using direct API calls to bypass create_index issues
"""
import os
import sys
import inspect
import importlib
import pymilvus
from pymilvus import MilvusClient, DataType

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def examine_milvus_client():
    """Examine the MilvusClient class for vector index methods."""
    # Print the module structure
    print(f"PyMilvus version: {pymilvus.__version__}")
    
    # Get the MilvusClient class
    client_class = MilvusClient
    
    # Get all methods
    methods = [
        method for method in dir(client_class) 
        if not method.startswith('_') and 
        callable(getattr(client_class, method))
    ]
    
    print(f"Available client methods: {', '.join(methods[:10])}...")
    
    # Look for index-related methods
    index_methods = [m for m in methods if 'index' in m.lower()]
    print(f"Index-related methods: {index_methods}")
    
    # Print signature of create_index
    if 'create_index' in methods:
        sig = inspect.signature(client_class.create_index)
        print(f"create_index signature: {sig}")
        
        # Get source code if possible
        try:
            source = inspect.getsource(client_class.create_index)
            print(f"create_index source (first 10 lines):")
            print('\n'.join(source.split('\n')[:10]))
        except Exception as e:
            print(f"Could not get source code: {e}")
    
    # Examine IndexParams
    try:
        from pymilvus.milvus_client.index import IndexParams
        print(f"Found IndexParams class")
        
        # Print its methods
        ip_methods = [m for m in dir(IndexParams) if not m.startswith('_')]
        print(f"IndexParams methods/attributes: {ip_methods}")
        
        # Print initialization signature
        ip_sig = inspect.signature(IndexParams.__init__)
        print(f"IndexParams.__init__ signature: {ip_sig}")
        
        try:
            ip_source = inspect.getsource(IndexParams.__init__)
            print(f"IndexParams.__init__ source (first 10 lines):")
            print('\n'.join(ip_source.split('\n')[:10]))
        except Exception as e:
            print(f"Could not get IndexParams source code: {e}")
            
    except ImportError:
        print("Could not find IndexParams class")
        
        # Look in milvus_client module
        if hasattr(pymilvus, 'milvus_client'):
            mc = pymilvus.milvus_client
            print(f"milvus_client attributes: {[a for a in dir(mc) if not a.startswith('_')][:20]}")
            
            # Check each module
            for attr in dir(mc):
                if not attr.startswith('_'):
                    module = getattr(mc, attr)
                    if inspect.ismodule(module):
                        print(f"Checking module {attr}")
                        for m_attr in dir(module):
                            if 'param' in m_attr.lower() or 'index' in m_attr.lower():
                                print(f"  Found potential match: {attr}.{m_attr}")

def create_custom_index():
    """Create index using direct API calls."""
    print(f"Connecting to Milvus at {DEFAULT_DB_PATH}")
    client = MilvusClient(uri=DEFAULT_DB_PATH)
    
    # Get the underlying grpc stub
    if hasattr(client, '_MilvusClient__stub'):
        print("Found client's grpc stub")
        stub = client._MilvusClient__stub
        
        # Try to create index directly using the stub
        try:
            # First get collection info
            collections = client.list_collections()
            print(f"Collections: {collections}")
            
            if "conversations" not in collections:
                print("'conversations' collection does not exist!")
                return False
                
            # Get collection info
            print("Getting collection info...")
            collection_info = client.describe_collection("conversations")
            print(f"Collection fields: {collection_info['schema']['fields']}")
            
            # Find the vector field
            vector_field = None
            for field in collection_info['schema']['fields']:
                if field['data_type'] == 'FloatVector':
                    vector_field = field
                    break
                    
            if not vector_field:
                print("No vector field found in the collection!")
                return False
                
            print(f"Found vector field: {vector_field['name']}")
            
            # Create index with direct RPC call
            print("Creating index with direct API calls...")
            
            # Try each available index creation approach
            
            # Approach 1: Through create_index_params
            if hasattr(MilvusClient, 'create_index_params'):
                try:
                    print("Using create_index_params method")
                    index_params = MilvusClient.create_index_params(
                        metric_type="COSINE",
                        index_type="HNSW",
                        params={"M": 8, "efConstruction": 64}
                    )
                    
                    client.create_index(
                        collection_name="conversations",
                        field_name="vector",
                        index_params=index_params
                    )
                    print("Index created successfully with create_index_params!")
                    return True
                except Exception as e:
                    print(f"create_index_params approach failed: {e}")
            
            # Approach 2: With Index class
            if hasattr(pymilvus, 'Index'):
                try:
                    print("Using Index class")
                    index = pymilvus.Index(
                        collection_name="conversations",
                        field_name="vector",
                        index_type="HNSW",
                        metric_type="COSINE",
                        params={"M": 8, "efConstruction": 64}
                    )
                    
                    client.create_index(
                        collection_name="conversations",
                        field_name="vector",
                        index_params=index
                    )
                    print("Index created successfully with Index class!")
                    return True
                except Exception as e:
                    print(f"Index class approach failed: {e}")
            
            print("All index creation approaches failed")
            return False
            
        except Exception as e:
            print(f"Error creating index directly: {e}")
            return False
    else:
        print("Could not access client's grpc stub")
        return False

if __name__ == "__main__":
    print("=== MILVUS INDEX EXAMINATION TOOL ===\n")
    
    # First examine the Milvus client
    examine_milvus_client()
    
    print("\n=== CUSTOM INDEX CREATION ===\n")
    
    # Try to create the index using direct calls
    if create_custom_index():
        print("\n✅ Successfully created index!")
    else:
        print("\n❌ Failed to create index!")
        
    print("\nSuggestion: If all approaches fail, consider switching to a different vector store backend, or using an older version of PyMilvus.")