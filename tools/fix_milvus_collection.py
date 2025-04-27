#!/usr/bin/env python3
"""
Fix script for PyMilvus 2.4.0 to work with local collection
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_pymilvus_version():
    """Check PyMilvus version."""
    try:
        result = subprocess.run(['pip', 'list', '--format=json'], capture_output=True, text=True)
        import json
        packages = json.loads(result.stdout)
        for pkg in packages:
            if pkg['name'] == 'pymilvus':
                print(f"PyMilvus version: {pkg['version']}")
                return pkg['version']
        print("PyMilvus not found")
        return None
    except Exception as e:
        print(f"Error checking PyMilvus version: {e}")
        return None

def start_milvus_server():
    """Start local Milvus server using Docker."""
    try:
        # Check if Docker is running
        docker_ps = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if docker_ps.returncode != 0:
            print("Docker is not running. Please start Docker first.")
            return False
            
        # Check if Milvus container is already running
        docker_ps = subprocess.run(['docker', 'ps', '--filter', 'name=milvus'], capture_output=True, text=True)
        if 'milvus' in docker_ps.stdout:
            print("Milvus container is already running.")
            return True
            
        # Start Milvus container
        print("Starting Milvus container...")
        docker_run = subprocess.run([
            'docker', 'run', '-d',
            '--name', 'milvus',
            '-p', '19530:19530',
            '-p', '9091:9091',
            'milvusdb/milvus:v2.3.3'
        ], capture_output=True, text=True)
        
        if docker_run.returncode != 0:
            print(f"Failed to start Milvus container: {docker_run.stderr}")
            return False
            
        print("Milvus container started. Waiting for it to initialize...")
        time.sleep(10)  # Wait for Milvus to initialize
        
        return True
    except Exception as e:
        print(f"Error starting Milvus server: {e}")
        return False

def fix_app_configs():
    """Update application code to use Milvus server instead of Milvus Lite."""
    # First, check if we need to modify ms_milvus_store.py
    milvus_store_path = os.path.expanduser("~/repos/scramble/scramble/magicscroll/ms_milvus_store.py")
    
    try:
        # Read the file
        with open(milvus_store_path, 'r') as f:
            content = f.read()
            
        # Check if it needs updating
        if "uri=self.db_path" in content:
            print(f"Updating {milvus_store_path} to use server URI...")
            
            # Update the content to use server URI
            content = content.replace(
                "uri=self.db_path", 
                "uri=\"http://localhost:19530\""
            )
            
            # Replace MilvusClient initialization
            content = content.replace(
                "self.client = MilvusClient(uri=self.db_path)",
                "self.client = MilvusClient(uri=\"http://localhost:19530\")"
            )
            
            # Write the updated content
            with open(milvus_store_path, 'w') as f:
                f.write(content)
                
            print(f"Updated {milvus_store_path}")
            return True
        else:
            print(f"No updates needed for {milvus_store_path}")
            return True
    except Exception as e:
        print(f"Error updating app configs: {e}")
        return False

def main():
    """Main entry point."""
    print("=== MILVUS COLLECTION FIX TOOL ===\n")
    
    # Check PyMilvus version
    version = check_pymilvus_version()
    if not version:
        print("PyMilvus not installed. Please install PyMilvus first.")
        return False
        
    # Check if we need to start Milvus server
    if not start_milvus_server():
        print("Failed to start Milvus server. Please check Docker installation.")
        return False
        
    # Update app configs to use Milvus server
    if not fix_app_configs():
        print("Failed to update app configs.")
        return False
        
    print("\n✅ Milvus configuration updated successfully!")
    print("\nImportant notes:")
    print("1. Make sure Docker is running whenever you use the application")
    print("2. The Milvus server is running in a Docker container named 'milvus'")
    print("3. You can stop it with: docker stop milvus")
    print("4. You can remove it with: docker rm milvus")
    
    return True

if __name__ == "__main__":
    main()