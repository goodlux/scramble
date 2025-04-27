#!/usr/bin/env python3
"""
Script to recreate the Milvus collection with proper index
"""
import os
import sys
import subprocess
import importlib

# Default Milvus database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def main():
    # Run direct shell command for debugging
    try:
        print("# Running direct shell commands to locate pymilvus")
        subprocess.run(["which", "python3"], check=True, text=True)
        subprocess.run(["pip", "list"], check=True, text=True)
        
        print("\n# Attempting to import pymilvus")
        import pymilvus
        print(f"PyMilvus version: {pymilvus.__version__}")
        
        # Find all available modules in pymilvus
        print("\n# Exploring pymilvus module structure:")
        for attr in dir(pymilvus):
            if not attr.startswith('_'):
                print(f"- {attr}")
        
        # Look for the IndexParams class
        print("\n# Looking for IndexParams class:")
        if hasattr(pymilvus, 'entity'):
            entity = pymilvus.entity
            print("Found pymilvus.entity module")
            for attr in dir(entity):
                if not attr.startswith('_'):
                    print(f"  - entity.{attr}")
                    
            # Check for index module
            if hasattr(entity, 'index'):
                index = entity.index
                print("  Found pymilvus.entity.index module")
                for attr in dir(index):
                    if not attr.startswith('_'):
                        print(f"    - entity.index.{attr}")
        
        # Test creating IndexParams
        print("\n# Testing IndexParams creation:")
        try:
            # Try to import it from different locations
            if hasattr(pymilvus.entity.index, 'Params'):
                IndexParams = pymilvus.entity.index.Params
                print("Found IndexParams at pymilvus.entity.index.Params")
            elif hasattr(pymilvus.entity, 'Params'):
                IndexParams = pymilvus.entity.Params
                print("Found IndexParams at pymilvus.entity.Params")
            elif hasattr(pymilvus, 'Params'):
                IndexParams = pymilvus.Params
                print("Found IndexParams at pymilvus.Params")
            else:
                print("Could not find IndexParams class!")
                return
                
            # Try to create an instance
            params_dict = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 8, "efConstruction": 64}
            }
            
            print("Creating IndexParams object...")
            try:
                # Try kwargs approach
                index_params = IndexParams(**params_dict)
                print("Successfully created IndexParams using kwargs!")
                print(f"IndexParams: {index_params}")
            except Exception as e:
                print(f"Error creating IndexParams with kwargs: {e}")
                
                try:
                    # Try direct constructor approach
                    index_params = IndexParams(
                        index_type="HNSW",
                        metric_type="COSINE",
                        params={"M": 8, "efConstruction": 64}
                    )
                    print("Successfully created IndexParams using direct constructor!")
                    print(f"IndexParams: {index_params}")
                except Exception as e2:
                    print(f"Error creating IndexParams with direct constructor: {e2}")
                    
            # Print the working approach for reference
            print("\n# SOLUTION - Copy this code:")
            print("""
# Import the IndexParams correctly
from pymilvus.entity.index import Params as IndexParams

# Create index parameters
index_params = IndexParams(
    index_type="HNSW",
    metric_type="COSINE", 
    params={"M": 8, "efConstruction": 64}
)

# Use in create_index
client.create_index(
    collection_name="conversations",
    field_name="vector",
    index_params=index_params
)
""")
                
        except Exception as e:
            print(f"Error testing IndexParams: {e}")
            
    except ModuleNotFoundError:
        print("pymilvus module not found in the current Python environment")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()