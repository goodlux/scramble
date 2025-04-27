# Scramble Development Guidelines

## Build & Test Commands
- Install dev dependencies: `pip install -e .`
- Start infrastructure: `docker-compose up -d`
- Run tests: `pytest tests/`
- Run single test: `pytest tests/test_file.py::test_function -v`
- Initialize Neo4j: `tools/init_neo4j.sh`
- Generate code index: `python tools/generate_code_index.py`

## Code Style
- **Imports**: Standard lib, third-party, local imports (in that order)
- **Type hints**: Required for all functions/methods with appropriate imports from `typing`
- **Classes**: PascalCase, inherit from base classes where appropriate
- **Functions/Methods**: snake_case, descriptive names
- **Documentation**: Docstrings for modules, classes, and methods using triple quotes
- **Error handling**: Specific exceptions, detailed error messages, use logger with context
- **Async**: Leverage async/await pattern for model interactions
- **Indentation**: 4 spaces, ~100 char line length

## Project Structure
- Core code in `scramble/` package
- CLI interfaces in `ramble/` and `ramblemaxx/`
- Graph database (Neo4j) for storage
- MagicScroll system for context management