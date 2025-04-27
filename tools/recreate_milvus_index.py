#!/usr/bin/env python3
"""
Script to create the proper Milvus index using the IndexType from pymilvus 2.5.7
"""
import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import pymilvus
    from pymilvus import MilvusClient, DataType, IndexType, MetricType
    print(f"PyMilvus version: {pymilvus.__version__}")
    
    # Check if IndexParams is available
    if hasattr(pymilvus, "IndexParams"):
        from pymilvus import IndexParams
        print("IndexParams class is available")
    else:
        print("IndexParams class not found in pymilvus")
        
except ImportError:
    print("PyMilvus not installed. Please install with: pip install pymilvus>=2.4.3")
    sys.exit(1)

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def create_index_for_pymilvus_2_5_7(db_path=None):
    """Create the index using the proper approach for PyMilvus 2.5.7."""
    db_path = db_path or DEFAULT_DB_PATH
    print(f"Using DB path: {db_path}")
    
    # Initialize Milvus connection
    try:
        client = MilvusClient(uri=db_path)
        print("Connected to Milvus successfully")
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        return False
    
    # List collections
    try:
        collections = client.list_collections()
        print(f"Collections: {collections}")
        
        if "conversations" not in collections:
            print("ERROR: 'conversations' collection not found")
            return False
        else:
            print("Found 'conversations' collection")
    except Exception as e:
        print(f"Failed to list collections: {e}")
        return False
    
    # Create index using the proper IndexParams object
    try:
        # For PyMilvus 2.5.7, we need to import the proper IndexParams class
        # and use it to create the index parameters
        print("Importing proper IndexParams from pymilvus module...")
        
        # Get the IndexParams class from the appropriate location
        try:
            # Import directly (correct for 2.5.7)
            from pymilvus.entity.index import Params as IndexParams
            print("Imported IndexParams from pymilvus.entity.index")
        except ImportError:
            try:
                # Try alternate import paths
                from pymilvus.entity import Params as IndexParams
                print("Imported IndexParams from pymilvus.entity")
            except ImportError:
                try:
                    # Try another alternate path
                    from pymilvus import Params as IndexParams
                    print("Imported IndexParams from pymilvus")
                except ImportError:
                    print("Could not import IndexParams class")
                    return False
        
        # Create the index parameters using the proper class
        print("Creating index parameters...")
        params = {"M": 8, "efConstruction": 64}
        
        # Try to create index parameters - multiple approaches
        try:
            # Approach 1: Use the IndexParams class directly
            index_params = IndexParams(
                index_type="HNSW",
                metric_type="COSINE",
                params=params
            )
            print("Successfully created IndexParams object")
        except Exception as e1:
            print(f"Error creating IndexParams object directly: {e1}")
            try:
                # Approach 2: Create dict and cast to IndexParams
                params_dict = {
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": params
                }
                index_params = IndexParams(**params_dict)
                print("Successfully created IndexParams object using **kwargs")
            except Exception as e2:
                print(f"Error creating IndexParams using dict: {e2}")
                return False
        
        # Create the index
        print("Creating index...")
        client.create_index(
            collection_name="conversations",
            field_name="vector",
            index_params=index_params
        )
        print("Successfully created index!")
        
        # Load the collection to verify the index works
        print("Loading collection...")
        client.load_collection("conversations")
        print("Collection loaded successfully")
        
        return True
    except Exception as e:
        print(f"Failed to create index: {e}")
        return False

if __name__ == "__main__":
    if create_index_for_pymilvus_2_5_7():
        print("✅ Successfully created index!")
    else:
        print("❌ Failed to create index!")