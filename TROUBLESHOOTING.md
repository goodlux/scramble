# Troubleshooting SQLite Vector Search in Scramble

If you're seeing errors related to SQLite vector search when starting Scramble, follow these steps to diagnose and fix the issues.

## Quick Fix

Run the macOS-specific fix script:

```bash
# Make the script executable
chmod +x tools/fix_sqlite_vec_macos.sh

# Run the script
tools/fix_sqlite_vec_macos.sh
```

## Diagnostic Steps

1. First, check if there are any issues with the SQLite vector extension:

```bash
# Make the script executable
chmod +x tools/check_db.py

# Run the diagnostic script
python tools/check_db.py
```

2. If issues are found, try reinstalling sqlite-vec:

```bash
# Make the script executable
chmod +x tools/reinstall_sqlite_vec.sh

# Run the reinstallation script
tools/reinstall_sqlite_vec.sh
```

3. For more detailed diagnostics, run the comprehensive check:

```bash
# Make the script executable
chmod +x tools/check_sqlite_vec.py

# Run the in-depth check
python tools/check_sqlite_vec.py
```

## Common Issues and Solutions

### No Such Module: vss0

This error