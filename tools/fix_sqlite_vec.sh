#!/bin/bash
# Script to fix SQLite vector search capability in Scramble

echo "🔧 Fixing sqlite-vec installation for Scramble"
echo "---------------------------------------------"

# Check Python version
python_version=$(python --version)
echo "Using Python: $python_version"

# Check SQLite version
sqlite_version=$(python -c "import sqlite3; print(f'SQLite version: {sqlite3.sqlite_version}')")
echo $sqlite_version

# Uninstall existing sqlite-vec if present
echo "Removing any existing sqlite-vec installation..."
pip uninstall -y sqlite-vec

# Install build dependencies if needed
echo "Installing build dependencies..."
pip install --upgrade pip wheel setuptools build

# Install sqlite-vec with force reinstall to ensure clean installation
echo "Installing sqlite-vec..."
pip install --force-reinstall sqlite-vec

# Verify installation
echo "Verifying installation..."
python -c "import sqlite_vec; print(f'sqlite-vec version: {sqlite_vec.__version__ if hasattr(sqlite_vec, \"__version__\") else \"Unknown\"}')"

if [ $? -eq 0 ]; then
    echo "✅ sqlite-vec installed successfully!"
    echo "You should now be able to run Scramble with vector search capability."
else
    echo "❌ There was a problem installing sqlite-vec."
    echo "Please try installing it manually with: pip install --force-reinstall sqlite-vec"
fi

echo ""
echo "If you continue to have issues, you may need to install sqlite-vec from source:"
echo "1. git clone https://github.com/asg017/sqlite-vec.git"
echo "2. cd sqlite-vec"
echo "3. pip install -e ."
echo ""

# Check for virtual environment
if [ -z "${VIRTUAL_ENV}" ]; then
    echo "⚠️ You don't appear to be in a virtual environment."
    echo "For best results, make sure to activate your virtual environment first:"
    echo "source .venv/bin/activate  # or wherever your virtualenv is"
fi
