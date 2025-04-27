# Setting up SQLite with Vector Search

scRAMble uses SQLite with the `sqlite-vec` extension for storing and searching chat history. This guide explains how to set up this component.

## Installing sqlite-vec

The [sqlite-vec](https://github.com/asg017/sqlite-vec) extension adds vector similarity search capabilities to SQLite, allowing scRAMble to perform semantic searches over past conversations.

### Easiest Method: pip

The simplest way to install sqlite-vec is using pip:

```bash
pip install sqlite-vec
```

This will install both the Python package and the necessary SQLite extension. The scRAMble code will automatically detect and use this package.

### Advanced Installation Methods

If you prefer to install the extension directly (not recommended for most users):

#### macOS

```bash
# Using Homebrew
brew install asg017/sqlite-ecosystem/sqlite-vec
```

#### Linux (Ubuntu/Debian)

```bash
# Install prerequisites
sudo apt-get update
sudo apt-get install -y sqlite3 libsqlite3-dev

# Download the latest release
LATEST_RELEASE=$(curl -s https://api.github.com/repos/asg017/sqlite-vec/releases/latest | grep "tag_name" | cut -d '"' -f 4)
curl -LO "https://github.com/asg017/sqlite-vec/releases/download/${LATEST_RELEASE}/sqlite-vec-linux-x86_64.tar.gz"

# Extract and install
tar -xzf sqlite-vec-linux-x86_64.tar.gz
sudo cp libsqlite_vec.so /usr/local/lib/
```

#### Windows

For Windows, download the latest release from the [GitHub releases page](https://github.com/asg017/sqlite-vec/releases) and follow the instructions in the README.

#### Using the install script

For a quick installation using the official install script:

```bash
curl -L https://github.com/asg017/sqlite-vec/releases/latest/download/install.sh | sh
```

## Troubleshooting

If scRAMble fails to load the sqlite-vec extension, check the logs for errors like:

```
WARNING: Could not load sqlite-vec extension; vector search will not be available
```

Common issues:

1. **Python package not installed**: Make sure you've installed the sqlite-vec package with pip
2. **SQLite version issues**: Some older versions of Python come with older SQLite versions that might not fully support extensions
3. **Permission issues**: On some systems, loading extensions may require additional permissions

## Adding to Requirements

If you're developing scRAMble, make sure to add sqlite-vec to your requirements.txt file:

```
sqlite-vec>=0.1.6
```
