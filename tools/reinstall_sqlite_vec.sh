#!/bin/bash
# Script to properly reinstall sqlite-vec from source

echo "🔄 Reinstalling sqlite-vec for Scramble"
echo "-------------------------------------"

# Check if we're in a virtual environment
if [ -z "${VIRTUAL_ENV}" ]; then
    echo "⚠️ No virtual environment detected"
    echo "It's recommended to run this within your virtual environment:"
    echo "source .venv/bin/activate  # or wherever your virtualenv is located"
    
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Uninstall existing sqlite-vec
echo "1️⃣ Removing existing sqlite-vec installation..."
pip uninstall -y sqlite-vec

# Install build dependencies
echo "2️⃣ Installing build dependencies..."
pip install --upgrade pip wheel setuptools build

# Try to install from PyPI first
echo "3️⃣ Attempting to install sqlite-vec from PyPI..."
pip install --force-reinstall sqlite-vec

# Test if the installation works
echo "4️⃣ Testing sqlite-vec installation..."
python -c "import sqlite_vec; import sqlite3; conn = sqlite3.connect(':memory:'); sqlite_vec.load(conn); print('Success!')" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ sqlite-vec installed successfully!"
else
    echo "⚠️ PyPI installation didn't work properly."
    echo "5️⃣ Attempting to install from source..."
    
    # Create a temporary directory
    TEMP_DIR=$(mktemp -d)
    cd $TEMP_DIR
    
    # Clone the repository
    git clone https://github.com/asg017/sqlite-vec.git
    cd sqlite-vec
    
    # Install from source
    pip install -e .
    
    # Test again
    python -c "import sqlite_vec; import sqlite3; conn = sqlite3.connect(':memory:'); sqlite_vec.load(conn); print('Success!')" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ sqlite-vec installed successfully from source!"
    else
        echo "❌ Failed to install sqlite-vec. Please check your system requirements."
        exit 1
    fi
    
    # Clean up
    cd -
    rm -rf $TEMP_DIR
fi

# Run the verification script
echo "6️⃣ Running full verification script..."
python /Users/rob/repos/scramble/tools/check_sqlite_vec.py

echo "Installation complete! You should now be able to run Scramble with vector search."
