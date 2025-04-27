#!/usr/bin/env python3
"""
Script to directly create a proper index for the Milvus collection
"""
import os
import sys
import importlib
import inspect

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def create_milvus_index():
    """Create a proper index for the Milvus collection."""
    try:
        import pymilvus
        from pymilvus import MilvusClient
        
        print(f"PyMilvus version: {pymilvus.__version__}")
        
        # Connect to Milvus
        client = MilvusClient(DEFAULT_DB_PATH)
        print(f"Connected to Milvus at {DEFAULT_DB_PATH}")
        
        # Check available collections
        collections = client.list_collections()
        print(f"Available collections: {collections}")
        
        if "conversations" not in collections:
            print("Error: 'conversations' collection not found.")
            return False
        
        # First, try to check if any index exists
        try:
            # This is a workaround to check for indexes
            # First try a search which will fail if no index exists
            import numpy as np
            dummy_vector = list(np.random.rand(384))
            
            # Try a search
            try:
                result = client.search(
                    collection_name="conversations",
                    data=[dummy_vector],
                    limit=1
                )
                print("Index exists and working!")
                return True
            except Exception as e:
                if "No index found" in str(e):
                    print("No index found, will create one.")
                    pass
                else:
                    print(f"Search error: {e}")
        except Exception as e:
            print(f"Error checking indexes: {e}")
        
        # Create a new index
        try:
            print("Creating index with modified approach...")
            
            # Modify the client.create_index method if needed
            if hasattr(client, 'create_index'):
                create_index_sig = inspect.signature(client.create_index)
                print(f"create_index signature: {create_index_sig}")
                
                # First approach - use class monkey-patching to get the class right
                try:
                    # Create the necessary classes and structures
                    import numpy as np
                    vector_field = np.random.rand(10, 384).astype(np.float32)
                    
                    # Check if we can import proper IndexParams
                    try:
                        # Try to import specific class
                        from pymilvus.milvus_client.index import IndexParams
                        print(f"IndexParams class found at pymilvus.milvus_client.index.IndexParams")
                        
                        # Create index
                        index_params = IndexParams(
                            index_type="FLAT",
                            metric_type="COSINE"
                        )
                        
                        client.create_index(
                            collection_name="conversations",
                            field_name="vector",
                            index_params=index_params
                        )
                        print("✅ Index created successfully using direct IndexParams class!")
                    except ImportError:
                        print("IndexParams not found in expected location, trying another approach...")
                        
                        # Try direct parameter passing
                        try:
                            # Try to call the method directly with modified parameters
                            client._MilvusClient__create_index(
                                collection_name="conversations",
                                field_name="vector",
                                index_type="FLAT",
                                metric_type="COSINE",
                                params={} 
                            )
                            print("✅ Index created successfully using direct method call!")
                        except Exception as e3:
                            print(f"Direct method call failed: {e3}")
                            return False
                            
                except Exception as e4:
                    print(f"Index creation failed: {e4}")
                    return False
            else:
                print("create_index method not found on client. Cannot create index.")
                return False
                
            # Verify if index is working
            try:
                client.load_collection("conversations")
                
                # Try a search
                import numpy as np
                dummy_vector = list(np.random.rand(384))
                
                result = client.search(
                    collection_name="conversations",
                    data=[dummy_vector],
                    limit=1
                )
                print("✅ Index successfully created and verified with search!")
                return True
            except Exception as e:
                print(f"Verification failed: {e}")
                return False
                
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
    except Exception as e:
        print(f"Initialization error: {e}")
        return False

if __name__ == "__main__":
    print("=== MILVUS INDEX CREATION TOOL ===\n")
    
    if create_milvus_index():
        print("\n✅ Index creation completed successfully!")
    else:
        print("\n❌ Index creation failed!")