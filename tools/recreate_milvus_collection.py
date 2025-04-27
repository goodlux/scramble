#!/usr/bin/env python3
"""
Script to recreate the Milvus collection with proper index
"""
import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import pymilvus
    from pymilvus import MilvusClient, DataType
    print(f"PyMilvus version: {pymilvus.__version__}")
except ImportError:
    print("PyMilvus not installed. Please install with: pip install pymilvus>=2.4.3")
    sys.exit(1)

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def recreate_milvus_collection(db_path=None):
    """Recreate the Milvus collection with proper schema and index."""
    db_path = db_path or DEFAULT_DB_PATH
    print(f"Using DB path: {db_path}")
    
    # Initialize Milvus connection
    try:
        client = MilvusClient(uri=db_path)
        print("Connected to Milvus successfully")
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        return False
    
    # Check if collection exists and drop it
    try:
        collections = client.list_collections()
        print(f"Existing collections: {collections}")
        
        if "conversations" in collections:
            print("Dropping existing 'conversations' collection")
            client.drop_collection("conversations")
            print("Collection dropped successfully")
    except Exception as e:
        print(f"Error checking/dropping collection: {e}")
        return False
    
    # Create schema using proper API
    print("Creating new 'conversations' collection")
    try:
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True
        )
        
        # Add fields to schema
        schema.add_field(
            field_name="id",
            datatype=DataType.INT64,
            is_primary=True
        )
        
        schema.add_field(
            field_name="orig_id",
            datatype=DataType.VARCHAR,
            max_length=64
        )
        
        schema.add_field(
            field_name="content",
            datatype=DataType.VARCHAR,
            max_length=65535
        )
        
        schema.add_field(
            field_name="entry_type",
            datatype=DataType.VARCHAR,
            max_length=32
        )
        
        schema.add_field(
            field_name="created_at",
            datatype=DataType.VARCHAR,
            max_length=64
        )
        
        schema.add_field(
            field_name="metadata",
            datatype=DataType.VARCHAR,
            max_length=65535
        )
        
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=384
        )
        
        # Create collection
        client.create_collection(
            collection_name="conversations",
            schema=schema
        )
        print("Collection created successfully")
        
        # Create index with different approaches
        print("Creating index...")
        success = False
        
        # Approach 1: Try using IndexParams if available
        try:
            try:
                from pymilvus import IndexParams
                index_params = IndexParams(
                    index_type="HNSW",
                    metric_type="COSINE",
                    params={"M": 8, "efConstruction": 64}
                )
            except ImportError:
                # Fall back to dict
                index_params = {
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": {"M": 8, "efConstruction": 64}
                }
            
            client.create_index(
                collection_name="conversations",
                field_name="vector",
                index_params=index_params
            )
            print("Vector index created successfully with approach 1")
            success = True
        except Exception as e:
            print(f"Approach 1 failed: {e}")
        
        # Approach 2: Try with direct parameters
        if not success:
            try:
                client.create_index(
                    collection_name="conversations",
                    field_name="vector", 
                    index_type="HNSW",
                    metric_type="COSINE", 
                    params={"M": 8, "efConstruction": 64}
                )
                print("Vector index created successfully with approach 2")
                success = True
            except Exception as e:
                print(f"Approach 2 failed: {e}")
        
        # Approach 3: Try with string parameters
        if not success:
            try:
                params = {
                    "index_type": "HNSW", 
                    "metric_type": "COSINE",
                    "params": {"M": 8, "efConstruction": 64}
                }
                client.create_index(
                    collection_name="conversations",
                    field_name="vector",
                    index_params=params
                )
                print("Vector index created successfully with approach 3")
                success = True
            except Exception as e:
                print(f"Approach 3 failed: {e}")
        
        # Load the collection
        if success:
            client.load_collection("conversations")
            print("Collection loaded into memory")
            print("Setup completed successfully!")
            return True
        else:
            print("All index creation approaches failed")
            return False
            
    except Exception as e:
        print(f"Error creating collection: {e}")
        return False

if __name__ == "__main__":
    if recreate_milvus_collection():
        print("✅ Successfully recreated Milvus collection with proper index!")
    else:
        print("❌ Failed to recreate Milvus collection!")