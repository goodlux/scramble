#!/bin/bash
# Script to fix sqlite-vec on macOS systems
# This is specifically to address issues with extension loading on macOS

echo "🔧 macOS SQLite Vector Extension Fix"
echo "====================================="

# Check Python version
echo "Python: $(python --version)"
echo "SQLite: $(python -c "import sqlite3; print(sqlite3.sqlite_version)")"

# Uninstall existing sqlite-vec
echo -e "\n1️⃣ Removing existing sqlite-vec installation..."
pip uninstall -y sqlite-vec

# Check if homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not installed. It's recommended for proper SQLite support."
    echo "   Visit https://brew.sh/ to install it"
else
    echo -e "\n2️⃣ Updating SQLite with Homebrew..."
    brew update
    brew install sqlite
    
    # Check for Python headers
    echo -e "\n3️⃣ Installing Python development headers..."
    brew install python3
fi

# Install sqlite-vec dependencies
echo -e "\n4️⃣ Installing build dependencies..."
pip install --upgrade pip wheel setuptools build

# Try installing from PyPI
echo -e "\n5️⃣ Installing sqlite-vec from PyPI..."
pip install --force-reinstall sqlite-vec

# Test the installation
echo -e "\n6️⃣ Testing sqlite-vec installation..."
python -c "import sqlite_vec; import sqlite3; conn = sqlite3.connect(':memory:'); conn.enable_load_extension(True); sqlite_vec.load(conn); print('Success!')" 

if [ $? -ne 0 ]; then
    echo -e "\n❌ Standard installation failed. Trying from source..."
    
    # Create a temporary directory
    TEMP_DIR=$(mktemp -d)
    cd $TEMP_DIR
    
    # Clone the repository
    git clone https://github.com/asg017/sqlite-vec.git
    cd sqlite-vec
    
    # Install from source
    pip install -e .
    
    # Test again
    echo -e "\nTesting source installation..."
    python -c "import sqlite_vec; import sqlite3; conn = sqlite3.connect(':memory:'); conn.enable_load_extension(True); sqlite_vec.load(conn); print('Success!')"
    
    # Clean up
    cd -
    rm -rf $TEMP_DIR
fi

echo -e "\n7️⃣ Creating a test database to verify vector operations..."
python3 - <<END
import sqlite3
import sqlite_vec
import numpy as np

# Create test database
conn = sqlite3.connect(':memory:')
conn.enable_load_extension(True)
sqlite_vec.load(conn)

try:
    # Try to create a vector table with vss0
    conn.execute("CREATE VIRTUAL TABLE test_vectors USING vss0(id TEXT, embedding BLOB, dimensions INTEGER, distance_function TEXT)")
    print("✅ Successfully created vss0 table")
except sqlite3.OperationalError as e:
    print(f"❌ Failed to create vss0 table: {e}")
    try:
        # Try with vec0
        conn.execute("CREATE VIRTUAL TABLE test_vectors USING vec0(id TEXT, embedding BLOB)")
        print("✅ Successfully created vec0 table (fallback)")
    except sqlite3.OperationalError as e:
        print(f"❌ Failed to create vec0 table: {e}")
        exit(1)

try:
    # Create a test vector
    test_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
    vector_blob = sqlite_vec.serialize_float32(test_vector)
    
    # Insert into table
    conn.execute("INSERT INTO test_vectors VALUES (?, ?, ?, ?)", 
                 ("test1", vector_blob, len(test_vector), "cosine"))
    
    print("✅ Vector operations successful!")
except Exception as e:
    print(f"❌ Vector operations failed: {e}")
    exit(1)
END

echo -e "\n8️⃣ Verifying your actual database..."
DB_PATH=~/.scramble/magicscroll.db

if [ -f "$DB_PATH" ]; then
    echo "✅ Database exists at $DB_PATH"
    
    # Check tables
    python3 - <<END
import sqlite3
import os

# Connect to the actual database
db_path = os.path.expanduser("~/.scramble/magicscroll.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Found tables: {[t[0] for t in tables]}")

# Check if entry_vectors exists
if any(t[0] == 'entry_vectors' for t in tables):
    print("✅ entry_vectors table exists")
else:
    print("❌ entry_vectors table does not exist")
    
# Check entries table
try:
    cursor.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    print(f"✅ entries table has {count} records")
except Exception as e:
    print(f"❌ Error accessing entries table: {e}")

# Close connection
conn.close()
END
else
    echo "❌ Database does not exist at $DB_PATH"
fi

echo -e "\n✨ Finished checking and fixing sqlite-vec"
echo "If issues persist, try running Scramble and check the logs for specific errors."
