# SQLite Vector Search Setup Guide

Scramble now uses SQLite with vector search capabilities (sqlite-vec) for storing and retrieving conversations based on semantic similarity.

## Troubleshooting SQLite-Vec Installation

If you see error messages like these when starting Scramble:

```
WARNING ms_sqlite_store.py:155 - Error creating vss0 table: no such module: vss0
ERROR ms_sqlite_store.py:168 - Error creating vec0 table: vec0 constructor error: Unknown table option: embedding
```

Follow these steps to resolve the issue:

### Option 1: Run the Fix Script

We've included a helper script to reinstall sqlite-vec properly:

```bash
# Make the script executable first
chmod +x /Users/rob/repos/scramble/tools/fix_sqlite_vec.sh

# Run the fix script
/Users/rob/repos/scramble/tools/fix_sqlite_vec.sh
```

### Option 2: Manual Installation

If the script doesn't work, you can manually install sqlite-vec by following these steps:

1. Activate your virtual environment (if you're using one):
   ```bash
   source .venv/bin/activate
   ```

2. Uninstall any existing sqlite-vec installation:
   ```bash
   pip uninstall -y sqlite-vec
   ```

3. Install build dependencies:
   ```bash
   pip install --upgrade pip wheel setuptools build
   ```

4. Reinstall sqlite-vec:
   ```bash
   pip install --force-reinstall sqlite-vec
   ```

5. Verify the installation:
   ```bash
   python -c "import sqlite_vec; print('sqlite-vec installed successfully')"
   ```

### Option 3: Install from Source

If the above options don't work, you can try building sqlite-vec from source:

```bash
git clone https://github.com/asg017/sqlite-vec.git
cd sqlite-vec
pip install -e .
```

## Checking if Vector Search is Working

When you start Scramble, look for these log messages:

- Success: `Search engine initialized with vector search capabilities`
- Fallback: `Search engine initialized with text-based fallback search`

Even if vector search isn't available, Scramble will still work with a text-based fallback search.

## SQLite Version Compatibility

sqlite-vec works best with SQLite 3.40.0 or newer. Check your SQLite version with:

```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

## Additional Notes

- The SQLite database file is stored at `~/.scramble/magicscroll.db`
- We use the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) embedding model, which produces 384-dimensional vectors
- Vector search uses cosine similarity for matching

If you continue to have issues, please open an issue on the GitHub repository or contact the development team.
