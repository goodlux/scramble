# MagicScroll Redis Implementation

This document describes the Redis implementation for MagicScroll persistent storage.

## Overview

MagicScroll uses Redis for two primary functions:
1. **Document storage** - storing conversation history and other entries
2. **Vector search** - semantic search using embeddings (via Redis search module)

## Setup

### Prerequisites

- Redis Stack Server with RedisSearch module
- Docker for containerized Redis (recommended)

### Environment Setup

Set the following environment variables before starting:
```bash
export REDIS_HOST=localhost    # Redis host
export REDIS_PORT=6379         # Redis port
export REDIS_CONTAINER_MODE=1  # Use 1 for Docker container access mode
```

Or simply use the provided script:
```bash
source tools/redis_env.sh
```

### Starting Redis

```bash
docker-compose up -d redis
```

## Usage

Start ramble with MagicScroll enabled:
```bash
./tools/start_ramble_with_magicscroll.sh
```

For CI/test mode:
```bash
./tools/start_ramble_with_magicscroll.sh --ci-mode
```

## Implementation Details

### Storage Components

1. **RedisDocumentStore** - Stores conversation entries and documents
2. **RedisVectorStore** - Stores vectors for semantic search (when available)
3. **Neo4j Graph Store** - Stores relationship graphs between entities

### Vector Search Architecture

The vector search implementation consists of:

1. **Embedding Generation**
   - Using HuggingFace's `all-MiniLM-L6-v2` model (384 dimensions)
   - Async embedding generation to avoid blocking

2. **Vector Storage**
   - Redis HNSW index for high-performance vector search
   - Cosine similarity metric for semantic matching
   - Index schema: `text TEXT`, `doc_id TEXT`, `embedding VECTOR FLOAT32 DIM 384`

3. **Search Operations**
   - K-nearest neighbors (KNN) search for semantic similarity
   - Hybrid filtering with temporal and type-based constraints
   - Container-mode compatible using Docker exec commands when needed

### MSSearch Class

The `MSSearch` class in `ms_search.py` provides the following functionality:

1. **Core Search Methods:**
   - `search()` - General-purpose semantic search with filters
   - `conversation_context_search()` - Optimized for finding conversation context

2. **Helper Methods:**
   - `_get_embedding()` - Generates embeddings for search queries
   - `_vector_search()` - Performs vector search operations
   - `_results_to_entries()` - Converts search results to MSEntry objects

### Docker Container Mode

When `REDIS_CONTAINER_MODE=1`, the system:
1. Uses local Redis client for basic operations
2. Uses `docker exec` for search module-specific operations
3. Creates vector indices directly using Redis commands

## Testing Vector Search

Use the provided test script to verify vector search functionality:

```bash
./tools/test_vector_store.sh
```

This script:
1. Verifies Redis search module availability
2. Creates a test vector index
3. Stores test documents with random embeddings
4. Performs basic and KNN vector searches
5. Validates search results

## Troubleshooting

If Redis search is not working:
1. Check if Redis Stack is running: `docker ps | grep redis`
2. Verify search module is loaded: `docker exec magicscroll-redis redis-cli MODULE LIST`
3. Check vector index creation: `docker exec magicscroll-redis redis-cli FT._LIST`
4. Inspect logs for Redis connection issues: `docker logs magicscroll-redis`
5. Test vector operations directly: `./tools/test_vector_store.sh`

### Common Issues

- **Search module not detected**: Ensure you're using Redis Stack, not standard Redis
- **Vector search not working**: Check index creation and embedding dimension (384)
- **Container connectivity**: Ensure your environment variables are set correctly

## Implementation Status

- ✅ Basic document storage
- ✅ Redis connection (both direct and container modes)
- ✅ Vector index creation when search module available
- ✅ Vector search implementation
- ✅ Conversation context search
- ✅ Temporal search filtering