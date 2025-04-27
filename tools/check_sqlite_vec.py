#!/usr/bin/env python3
"""
Script to verify that sqlite-vec is correctly installed and working
"""

import os
import sys
import sqlite3
import importlib.util

def check_sqlite_version():
    """Check SQLite version"""
    print(f"SQLite version: {sqlite3.sqlite_version}")
    version_tuple = tuple(map(int, sqlite3.sqlite_version.split('.')))
    if version_tuple < (3, 40, 0):
        print("⚠️ WARNING: Your SQLite version is older than 3.40.0, which might cause issues with sqlite-vec")
        return False
    return True

def check_sqlite_vec_installed():
    """Check if sqlite-vec is installed"""
    spec = importlib.util.find_spec("sqlite_vec")
    if spec is None:
        print("❌ sqlite-vec is NOT installed")
        print("Run: pip install sqlite-vec")
        return False
    
    print("✅ sqlite-vec module is installed")
    try:
        import sqlite_vec
        print(f"sqlite-vec version: {getattr(sqlite_vec, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"❌ Error importing sqlite_vec: {e}")
        return False

def check_extension_loading():
    """Check if the SQLite extension can be loaded"""
    try:
        import sqlite_vec
        conn = sqlite3.connect(':memory:')
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        
        # Check if the extension functions are available
        try:
            version = conn.execute("SELECT vec_version()").fetchone()[0]
            print(f"✅ Extension loaded successfully: vec_version = {version}")
            return True
        except sqlite3.OperationalError:
            try:
                version = conn.execute("SELECT vss_version()").fetchone()[0]
                print(f"✅ Extension loaded successfully: vss_version = {version}")
                return True
            except sqlite3.OperationalError as e:
                print(f"❌ Extension loaded but functions not available: {e}")
                return False
    except Exception as e:
        print(f"❌ Failed to load extension: {e}")
        return False

def check_vector_operations():
    """Test basic vector operations"""
    try:
        import sqlite_vec
        import numpy as np
        
        conn = sqlite3.connect(':memory:')
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        
        # Try to create a vector table
        try:
            conn.execute('''
            CREATE VIRTUAL TABLE test_vectors USING vss0(
                id TEXT,
                embedding BLOB,
                dimensions INTEGER,
                distance_function TEXT
            )
            ''')
            print("✅ Created vector table using vss0")
        except sqlite3.OperationalError as e1:
            print(f"⚠️ Could not create vss0 table: {e1}")
            try:
                conn.execute('''
                CREATE VIRTUAL TABLE test_vectors USING vec0(
                    id TEXT,
                    embedding BLOB
                )
                ''')
                print("✅ Created vector table using vec0")
            except sqlite3.OperationalError as e2:
                print(f"❌ Could not create vector table: {e2}")
                return False
        
        # Insert a test vector
        try:
            test_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
            embedding_blob = sqlite_vec.serialize_float32(test_vector)
            
            conn.execute(
                "INSERT INTO test_vectors VALUES (?, ?, ?, ?)",
                ("test1", embedding_blob, len(test_vector), "cosine")
            )
            print("✅ Inserted test vector")
            
            # Query the vector
            result = conn.execute("SELECT * FROM test_vectors").fetchone()
            print(f"✅ Retrieved vector: {result[0]}")
            
            return True
        except Exception as e:
            print(f"❌ Vector operations failed: {e}")
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main entry point"""
    print("\n🔍 Checking sqlite-vec installation\n")
    
    # Run all checks
    sqlite_version_ok = check_sqlite_version()
    sqlite_vec_installed = check_sqlite_vec_installed()
    extension_loads = check_extension_loading() if sqlite_vec_installed else False
    vector_ops_ok = check_vector_operations() if extension_loads else False
    
    # Overall status
    print("\n📊 Results:")
    print(f"SQLite version check: {'✅' if sqlite_version_ok else '⚠️'}")
    print(f"sqlite-vec installed: {'✅' if sqlite_vec_installed else '❌'}")
    print(f"Extension loads properly: {'✅' if extension_loads else '❌'}")
    print(f"Vector operations work: {'✅' if vector_ops_ok else '❌'}")
    
    if all([sqlite_version_ok, sqlite_vec_installed, extension_loads, vector_ops_ok]):
        print("\n✅ sqlite-vec is correctly installed and working!")
        return 0
    else:
        print("\n⚠️ There are issues with your sqlite-vec installation")
        print("\nTo fix these issues, try the following steps:")
        print("1. Uninstall sqlite-vec: pip uninstall -y sqlite-vec")
        print("2. Make sure you have the latest pip: pip install --upgrade pip")
        print("3. Install build dependencies: pip install --upgrade wheel setuptools build")
        print("4. Reinstall sqlite-vec: pip install sqlite-vec")
        print("\nIf problems persist, try installing from source:")
        print("pip install git+https://github.com/asg017/sqlite-vec")
        return 1

if __name__ == "__main__":
    sys.exit(main())
