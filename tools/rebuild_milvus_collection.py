#!/usr/bin/env python3
"""
Script to rebuild the Milvus collection for MagicScroll
"""
import os
import sys
from pathlib import Path
import pymilvus
from pymilvus import MilvusClient, DataType

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def rebuild_milvus_collection():
    """Rebuild the Milvus collection with proper schema and attempt to create index."""
    # Print PyMilvus version
    print(f"PyMilvus version: {pymilvus.__version__}")
    
    # Connect to Milvus
    db_path = DEFAULT_DB_PATH
    print(f"Using Milvus database at: {db_path}")
    
    client = MilvusClient(uri=db_path)
    print("Connected to Milvus successfully")
    
    # Check if collection exists
    collections = client.list_collections()
    print(f"Existing collections: {collections}")
    
    # Drop collection if it exists
    if "conversations" in collections:
        print("Dropping existing 'conversations' collection")
        client.drop_collection("conversations")
        print("Collection dropped successfully")
    
    # Create new collection with schema
    print("Creating new 'conversations' collection")
    
    schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=True
    )
    
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
    
    # Attempt to create index - we'll try both with Index class and without
    print("\nAttempting to create index...")
    
    # Approach with Index class if available
    if hasattr(pymilvus, 'Index'):
        try:
            print("Creating index using Index class:")
            
            # Create index parameters
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 8, "efConstruction": 64}
            }
            
            # Create an Index object
            index_obj = pymilvus.Index(
                collection_name="conversations",
                field_name="vector",
                params=index_params
            )
            
            # Create the index
            client.create_index(
                collection_name="conversations",
                field_name="vector",
                index_params=index_obj
            )
            
            print("✅ Index created successfully using Index class!")
            return True
        except Exception as e:
            print(f"❌ Failed to create index using Index class: {e}")
    
    # Try alternate approach - with dictionary
    try:
        print("\nCreating index using dictionary approach:")
        
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
        
        print("✅ Index created successfully using dictionary approach!")
        return True
    except Exception as e:
        print(f"❌ Failed to create index using dictionary approach: {e}")
    
    # Try another approach - with kwargs
    try:
        print("\nCreating index with kwargs directly:")
        
        client.create_index(
            collection_name="conversations",
            field_name="vector", 
            index_type="HNSW",
            metric_type="COSINE", 
            params={"M": 8, "efConstruction": 64}
        )
        
        print("✅ Index created successfully using kwargs directly!")
        return True
    except Exception as e:
        print(f"❌ Failed to create index using kwargs directly: {e}")
    
    # Try more direct approach - minimal params
    try:
        print("\nCreating index with minimal params:")
        
        client.create_index(
            collection_name="conversations",
            field_name="vector",
            index_type="HNSW"
        )
        
        print("✅ Index created successfully with minimal params!")
        return True
    except Exception as e:
        print(f"❌ Failed to create index with minimal params: {e}")
    
    # Try with a new builder class
    try:
        print("\nCreating index using get_index_from_params:")
        
        # Try to get the create_index_params function (this is the 2.5.7+ API)
        if hasattr(MilvusClient, 'create_index_params'):
            print("Found create_index_params method")
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
            
            print("✅ Index created successfully using get_index_from_params!")
            return True
    except Exception as e:
        print(f"❌ Failed to create index using get_index_from_params: {e}")
    
    print("\n❌ All index creation attempts failed!")
    return False

if __name__ == "__main__":
    print("=== MILVUS COLLECTION REBUILD TOOL ===")
    
    if rebuild_milvus_collection():
        print("\n✅ Successfully rebuilt Milvus collection!")
    else:
        print("\n❌ Failed to complete Milvus collection rebuild with index.")