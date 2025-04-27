# scRAMble MAXX
 
Semantically compressed RAM-based language exchange

Featuring rambleMAXX: the AI enhanced terminal chat interface from the 1980's, now with Magic Scroll technology!

## Features

- **Multi-model chat client** - Communicate with both local and remote LLMs seamlessly
- **Context-aware chat** - Smart retrieval of relevant conversation history
- **SQLite-powered database** - Self-contained storage with vector search capabilities
- **Terminal-based UI** - Clean, efficient interface for maximum productivity

## Installation

From source:
```bash
# Clone the repository
git clone https://github.com/yourusername/scramble.git
cd scramble

# Install dependencies and the package in development mode
pip install -e .
```

## Usage

Start the interactive CLI:
```bash
./tools/start_ramble.sh
```

Or take it to the MAXX with rambleMAXX:
```bash
maxx
```

## Requirements

- Python 3.8+
- sentence-transformers
- sqlite-vec (automatically installed with package)
- ollama (optional, for local models)

## Architecture

scRAMble uses a SQLite database with vector search capabilities to store and retrieve chat conversations. This approach offers several advantages:

1. **Self-contained** - Everything is stored in a single file (~/.scramble/magicscroll.db)
2. **Fast retrieval** - Vector similarity search for finding relevant context
3. **No external dependencies** - No need to run separate database servers

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development guidelines.

For SQLite vector search setup, see [docs/SQLITE_SETUP.md](docs/SQLITE_SETUP.md).

## License

MIT
