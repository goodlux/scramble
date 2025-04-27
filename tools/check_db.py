#!/usr/bin/env python3
"""
Simple script to check the SQLite database and vector extension
"""

import os
import sqlite3
import sys

# Path to the database
DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

def check_database():
    """Check if the database exists and is accessible"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    print(f"✅ Database found at {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        print("✅ Successfully connected to database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

def get_tables(conn):
    """Get list of tables in the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in database")
            return False
        
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        return [t[0] for t in tables]
    except Exception as e:
        print(f"❌ Failed to get tables: {e}")
        return False

def check_vector_extension(conn):
    """Check if vector extension is available"""
    try:
        # Try to import sqlite_vec
        try:
            import sqlite_vec
            print("✅ sqlite_vec module imported successfully")
        except ImportError:
            print("❌ Failed to import sqlite_vec module")
            return False
        
        # Try to load the extension
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            print("✅ Successfully loaded sqlite_vec extension")
        except Exception as e:
            print(f"❌ Failed to load sqlite_vec extension: {e}")
            return False
        
        # Check if vector functions are available
        try:
            cursor = conn.cursor()
            try:
                version = cursor.execute("SELECT vec_version()").fetchone()
                print(f"✅ Vector functions available: vec_version = {version[0]}")
            except sqlite3.OperationalError:
                try:
                    version = cursor.execute("SELECT vss_version()").fetchone()
                    print(f"✅ Vector functions available: vss_version = {version[0]}")
                except sqlite3.OperationalError:
                    print("❌ No vector functions available")
                    return False
        except Exception as e:
            print(f"❌ Failed to check vector functions: {e}")
            return False
        
        return True
    finally:
        try:
            conn.enable_load_extension(False)
        except:
            pass
        
def main():
    """Main function"""
    print("\n🔍 Checking SQLite database and vector extension\n")
    
    # Check database
    conn = check_database()
    if not conn:
        return 1
    
    # Get tables
    tables = get_tables(conn)
    if not tables:
        conn.close()
        return 1
    
    # Check for entry_vectors table
    if 'entry_vectors' in tables:
        print("✅ entry_vectors table found")
    else:
        print("❌ entry_vectors table not found")
    
    # Check vector extension
    vector_extension_ok = check_vector_extension(conn)
    
    # Close connection
    conn.close()
    
    if vector_extension_ok:
        print("\n✅ Vector extension is working properly!")
        return 0
    else:
        print("\n❌ Issues found with vector extension")
        print("\nTo fix these issues, run:")
        print("  /Users/rob/repos/scramble/tools/reinstall_sqlite_vec.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())
