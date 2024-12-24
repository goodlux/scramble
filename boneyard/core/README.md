# Scramble Boneyard

This directory contains the original core components of Scramble from when it was primarily a semantic compression system. While these components have been superseded by newer implementations, they're preserved here for reference as they contain some interesting approaches and implementations.

## Notable Components

### Semantic Compressor (compressor.py)
- Sophisticated semantic compression engine
- Variable compression levels (LOW/MEDIUM/HIGH)
- Smart chunk management with semantic similarity scoring
- Uses sentence-transformers for embeddings
- Includes adaptive chunk combining based on semantic similarity

### Context Store System (store.py, context.py)
- Sophisticated context management system
- Hierarchical chain building with parent/child relationships
- Advanced context scoring and selection
- Natural language time-based context retrieval
- Automatic reindexing and recovery
- Full and compressed version management

### Original API Client (api.py)
- Anthropic API integration with context awareness
- Smart system message building with timestamped contexts
- Simultaneous management of compressed and full conversation versions
- Token usage tracking
- Message history management with configurable window
- Context-aware conversation threading

### Original Scroll System (scroll.py, scroll_manager.py)
- Predecessor to MagicScroll
- Simple but effective timeline-based interaction storage
- Threading support via parent_id linking
- Flexible filtering system

### Stats System (stats.py)
- Comprehensive compression statistics tracking
- Token usage monitoring
- CLI reporting with rich tables
- Historical performance analysis

These implementations represent early design decisions that evolved into the current MagicScroll-based system. They're maintained here for:
1. Historical reference
2. Potential reuse of specific algorithms
3. Documentation of the project's evolution

## Notable Features Worth Preserving

### Context and Storage Management
1. Context Selection Logic
   - Multi-factor scoring (recency, semantic similarity, chain relationships)
   - Natural language time reference parsing
   - Token budget management
   - Automatic chain building

2. Storage Management
   - Robust error handling and recovery
   - Automatic reindexing
   - Support for both full and compressed versions
   - Rich metadata tracking

3. Chain Building
   - Parent/child relationship tracking
   - Automatic chain reconstruction
   - Efficient traversal algorithms

### Conversation Management
1. System Message Building
   - Context-aware prompt construction
   - Timestamp-based reference system
   - Smart context selection and integration

2. Version Control
   - Parallel management of full and compressed versions
   - Rich metadata tracking
   - Token usage optimization

3. Performance Features
   - Caching and lazy loading
   - Efficient similarity calculations
   - Smart context window management
   - Configurable compression levels