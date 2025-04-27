#!/usr/bin/env python3
"""
Direct fix for Milvus index using the IndexParams class structure from pymilvus 2.5.7
"""
import os
import sys
from pathlib import Path
import pymilvus
from pymilvus import MilvusClient, DataType

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

class DummyIndexParams:
    """A dummy class to replicate the expected IndexParams structure."""
    
    def __init__(self, index_type="HNSW", metric_type="COSINE", params=None):
        """Initialize with necessary parameters."""
        self.index_type = index_type
        self.metric_type = metric_type
        self.params = params or {"M": 8, "efConstruction": 64}
        
    def __str__(self):
        """String representation."""
        return f"IndexParams(index_type={self.index_type}, metric_type={self.metric_type}, params={self.params})"

def fix_milvus_index():
    """Fix the Milvus index by emulating the expected IndexParams structure."""
    print(f"PyMilvus version: {pymilvus.__version__}")
    
    # Connect to Milvus
    client = MilvusClient(uri=DEFAULT_DB_PATH)
    print(f"Connected to Milvus at {DEFAULT_DB_PATH}")
    
    # List collections
    collections = client.list_collections()
    print(f"Collections: {collections}")
    
    if "conversations" not in collections:
        print("'conversations' collection does not exist!")
        return False
    
    # Create a dummy IndexParams object
    index_params = DummyIndexParams()
    print(f"Created dummy IndexParams: {index_params}")
    
    # Attempt to create the index using the index_params object
    try:
        # Extract parameters as needed by the MilvusClient.create_index method
        # Examine the signature
        import inspect
        sig = inspect.signature(MilvusClient.create_index)
        print(f"create_index signature: {sig}")
        
        # Try direct approach using our custom IndexParams
        try:
            from pymilvus.milvus_client.index import IndexParams
            print("Found IndexParams at pymilvus.milvus_client.index")
            
            # Create with proper IndexParams class
            params = {"M": 8, "efConstruction": 64}
            index_params = IndexParams(
                index_type="HNSW",
                metric_type="COSINE",
                params=params
            )
            
            client.create_index(
                collection_name="conversations",
                field_name="vector",
                index_params=index_params
            )
            print("Index created successfully!")
            return True
        except ImportError:
            print("Could not import IndexParams from pymilvus.milvus_client.index")
        
        # Try another approach - monkey patching
        try:
            # Patch in our own IndexParams to match the expected format
            pymilvus.milvus_client.index.IndexParams = DummyIndexParams
            
            index_params = DummyIndexParams()
            client.create_index(
                collection_name="conversations",
                field_name="vector",
                index_params=index_params
            )
            print("Index created successfully with monkey patching!")
            return True
        except Exception as e:
            print(f"Monkey patching approach failed: {e}")
        
        print("All approaches failed!")
        return False
    except Exception as e:
        print(f"Error creating index: {e}")
        return False

if __name__ == "__main__":
    print("=== MILVUS INDEX DIRECT FIX TOOL ===")
    
    if fix_milvus_index():
        print("\n✅ Successfully fixed Milvus index!")
    else:
        print("\n❌ Failed to fix Milvus index!")