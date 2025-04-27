#!/usr/bin/env python3
"""
Simple test for sqlite-vec 
"""
import sqlite3
import os

# Try importing sqlite-vec
print("Testing sqlite-vec import...")
try:
    import sqlite_vec
    print("✅ sqlite-vec module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import sqlite-vec: {e}")
    print("Run: pip install --force-reinstall sqlite-vec")
    exit(1)

# Try loading the extension
print("\nTesting extension loading...")
conn = sqlite3.connect(':memory:')
try:
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    print("✅ Successfully loaded the extension")
except Exception as e:
    print(f"❌ Failed to load extension: {e}")
    exit(1)

# Try vector functions
print("\nTesting vector functions...")
try:
    # Create a test table with vector column
    conn.execute("CREATE VIRTUAL TABLE test_vectors USING vss0(id, vector BLOB, dimensions INT, distance TEXT)")
    print("✅ Created test vector table with vss0")
except sqlite3.OperationalError as e:
    print(f"⚠️ vss0 extension not available: {e}")
    try:
        conn.execute("CREATE VIRTUAL TABLE test_vectors USING vec0(id, vector BLOB)")
        print("✅ Created test vector table with vec0")
    except sqlite3.OperationalError as e:
        print(f"❌ vec0 extension not available: {e}")
        print("Vector search functionality is not available")
        exit(1)

print("\n✅ sqlite-vec is working properly!")
