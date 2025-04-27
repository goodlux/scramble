# Vector Search in Scramble

## Overview

Scramble uses SQLite with vector search capabilities via the `sqlite-vec` extension. Vector search is a critical component that allows semantic matching of conversations and messages. This document explains how to properly set up and verify the vector search functionality.

## Requirements

- Python 3.10+
- SQLite 3.40.0+
- pip and build tools
- The `sqlite-vec` extension

## Checking Your Setup

We've provided a tool to check if your vector search setup is working properly:

```bash
python tools/check_sqlite_vec.py
```

This script will verify:
1. Your SQLite version
2. If `sqlite-vec` is installed
3. If the extension loads properly
4. If vector operations work correctly

## Fixing Vector Search Issues

If you encounter errors with vector search, such as:

```
Error creating vss0 table: no such module: vss0
Error creating vec0 table: vec0 constructor error: Unknown table option: embedding
```

Use our reinstallation script:

```bash
# Make the script executable
chmod +x tools/reinstall_sqlite_vec.sh

# Run the script
./tools/reinstall_sqlite_vec.sh
```

This script will:
1. Uninstall any existing `sqlite-vec` installation
2. Install necessary build dependencies
3. Reinstall `sqlite-vec` from PyPI
4. If that fails, install from source
5. Verify the installation works correctly

## Verifying Vector Search is Working

When Scramble starts, look for this log message to confirm vector search is working:

```
Search engine initialized with vector search capabilities
```

If you see error messages about vector search not being available, it means the setup isn't working correctly.

## Manual Installation

If the automated scripts don't work, you can manually install `sqlite-vec`:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Uninstall existing installation
pip uninstall -y sqlite-vec

# Install build dependencies
pip install --upgrade pip wheel setuptools build

# Try installing from PyPI first
pip install --force-reinstall sqlite-vec

# Test the installation
python -c "import sqlite_vec; import sqlite3; conn = sqlite3.connect(':memory:'); sqlite_vec.load(conn); print('Success!')"

# If that doesn't work, install from source
git clone https://github.com/asg017/sqlite-vec.git
cd sqlite-vec
pip install -e .
```

## Troubleshooting

If you continue to have issues:

1. **Check your SQLite version**:
   ```python
   python -c "import sqlite3; print(sqlite3.sqlite_version)"
   ```
   It should be 3.40.0 or higher.

2. **Make sure your Python environment has development headers**:
   ```bash
   # On macOS
   brew install python-dev
   
   # On Ubuntu/Debian
   sudo apt-get install python3-dev
   ```

3. **Check if extension loading is enabled**:
   ```python
   python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.enable_load_extension(True); print('Extension loading enabled')"
   ```
   If this throws an error, your SQLite doesn't support extension loading.

## Importance of Vector Search

Vector search is a critical component of Scramble:

- It enables semantic matching of conversations rather than just keyword matching
- It powers the context-aware chat features by finding relevant past conversations
- It allows searching for concepts and ideas rather than just exact phrases

Without working vector search, the application will fail to provide these important features.

## Technical Details

- Scramble uses the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) embedding model
- Embeddings are 384-dimensional vectors
- Search uses cosine similarity for matching
- Vector data is stored in the SQLite database at `~/.scramble/magicscroll.db`
