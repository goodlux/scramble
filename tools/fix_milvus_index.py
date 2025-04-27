#!/usr/bin/env python3
"""
Script to fix Milvus index issues
"""
import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import pymilvus 
try:
    from pymilvus import MilvusClient, IndexType
    print(f"Successfully imported pymilvus")
except ImportError:
    print("pymilvus not installed")
    sys.exit(1)

# Import necessary scramble modules
try:
    from scramble.utils.logging import get_logger
    from scramble.magicscroll.ms_milvus_store import MSMilvusStore
    print("Successfully imported scramble modules")
except ImportError as e:
    print(f"Failed to import scramble modules: {e}")
    sys.exit(1)

# Set up logging
logger = get_logger(__name__)

def fix_milvus_index():
    """Create a collection and index to test different index_params formats"""
    
    # Use default db path
    db_path = os.path.expanduser("~/.scramble/magicscroll.db")
    print(f"Using DB path: {db_path}")
    
    # Connect to Milvus
    try:
        client = MilvusClient(uri=db_path)
        print("Connected to Milvus successfully")
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        return
    
    # List collections
    try:
        collections = client.list_collections()
        print(f"Collections: {collections}")
    except Exception as e:
        print(f"Failed to list collections: {e}")
    
    # Try different index formats
    if "conversations" in collections:
        # Try format 1: Using dictionaries
        try:
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 8, "efConstruction": 64}
            }
            print(f"Trying index creation with params: {index_params}")
            client.create_index(
                collection_name="conversations",
                field_name="vector",
                index_params=index_params
            )
            print("Index created successfully!")
        except Exception as e:
            print(f"Format 1 failed: {e}")
            
            # Try format 2: Using strings
            try:
                index_params = {
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": {"M": 8, "efConstruction": 64}
                }
                print(f"Trying index creation with params: {index_params}")
                client.create_index(
                    collection_name="conversations",
                    field_name="vector",
                    index_params=index_params
                )
                print("Index created successfully!")
            except Exception as e:
                print(f"Format 2 failed: {e}")
                
                # Try format 3: Using json string
                try:
                    import json
                    index_params_str = json.dumps({
                        "index_type": "HNSW",
                        "metric_type": "COSINE",
                        "params": {"M": 8, "efConstruction": 64}
                    })
                    print(f"Trying index creation with params string: {index_params_str}")
                    client.create_index(
                        collection_name="conversations",
                        field_name="vector",
                        index_params=index_params_str
                    )
                    print("Index created successfully!")
                except Exception as e:
                    print(f"Format 3 failed: {e}")

if __name__ == "__main__":
    fix_milvus_index()