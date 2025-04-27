#!/usr/bin/env python3
"""
Test script for PyMilvus with Milvus Lite to verify index creation and vector search.
For PyMilvus 2.4.0
"""
import os
import sys
import numpy as np
import pymilvus
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from pymilvus.orm.types import CONSISTENCY_BOUNDED

# Print pymilvus version for verification
print(f"PyMilvus version: {pymilvus.__version__}")

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll_test.db")

def test_milvus_lite():
    """Test basic PyMilvus-Lite functionality including index creation and search."""
    print(f"PyMilvus version: {pymilvus.__version__}")
    
    # Connect to Milvus using ORM API (PyMilvus 2.4.0 style)
    print(f"Connecting to Milvus Lite")
    try:
        connections.connect(
            alias="default",
            uri="http://localhost:19530",  # Standard URI format
            user="",
            password="",
            db_name=""
        )
        print("Connected successfully using URI format")
    except Exception as e:
        print(f"URI connection failed: {e}")
        
        # Try connecting to lite version
        try:
            connections.connect("default", db_name="lite", uri="lite://" + DEFAULT_DB_PATH)
            print("Connected successfully using lite:// URI format")
        except Exception as e2:
            print(f"Lite URI connection failed: {e2}")
            return False
    
    # Check for existing collections
    print("Checking existing collections")
    existing_collections = utility.list_collections()
    print(f"Existing collections: {existing_collections}")
    
    # Drop test_collection if it exists
    if "test_collection" in existing_collections:
        print("Dropping existing test_collection")
        utility.drop_collection("test_collection")
    
    # Create collection with schema
    print("Creating test_collection")
    
    # Define fields
    fields = [
        FieldSchema(
            name="id", 
            dtype=DataType.INT64, 
            is_primary=True
        ),
        FieldSchema(
            name="text", 
            dtype=DataType.VARCHAR, 
            max_length=1024
        ),
        FieldSchema(
            name="vector", 
            dtype=DataType.FLOAT_VECTOR, 
            dim=4  # Small dimension for testing
        ),
    ]
    
    # Define schema
    schema = CollectionSchema(
        fields=fields,
        description="Test collection for PyMilvus 2.4.0"
    )
    
    # Create collection
    collection = Collection(
        name="test_collection",
        schema=schema,
        consistency_level=CONSISTENCY_BOUNDED
    )
    print("Collection created successfully")
    
    # Insert data
    print("Inserting test data")
    entities = [
        [1, 2, 3],  # id field
        ["This is a test", "Another test example", "Final test case"],  # text field
        [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6]
        ]  # vector field
    ]
    
    # Insert data
    collection.insert(entities)
    print("Data inserted successfully")
    
    # Create index - the critical part
    print("Creating index on vector field")
    try:
        # Create index params
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 8, "efConstruction": 64}
        }
        
        # Create index
        collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        print("✅ Index created successfully!")
    except Exception as e:
        print(f"❌ Index creation failed: {e}")
        return False
    
    # Load collection
    collection.load()
    print("Collection loaded successfully")
    
    # Perform vector search
    print("Testing vector search")
    query_vector = [[0.2, 0.3, 0.4, 0.5]]  # Same as second vector
    
    try:
        # Define search parameters
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 32}
        }
        
        # Perform search
        results = collection.search(
            data=query_vector,
            anns_field="vector",
            param=search_params,
            limit=2,
            output_fields=["text"]
        )
        
        print("✅ Search performed successfully!")
        print(f"Number of results: {len(results)}")
        
        # Check results
        if results and len(results) > 0:
            result = results[0]
            ids = result.ids
            print(f"Result IDs: {ids}")
            
            if 2 in ids:
                print("✅ Search result contains the expected ID!")
            else:
                print("❌ Search result doesn't contain expected ID")
                
            # Print distances
            print(f"Distances: {result.distances}")
            
            return True
        else:
            print("No search results found")
            return False
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False

if __name__ == "__main__":
    print("=== MILVUS LITE TEST SCRIPT ===\n")
    
    success = test_milvus_lite()
    
    if success:
        print("\n✅ PyMilvus Lite test completed successfully!")
    else:
        print("\n❌ PyMilvus Lite test failed!")