#!/bin/bash
# Test script for Redis vector store configuration and search functionality

# Source the Redis environment setup
source tools/redis_env.sh

# Docker container name
CONTAINER="magicscroll-redis"

# Check if Redis search module is available
echo "Testing Redis search module availability..."
SEARCH_MODULE=$(docker exec $CONTAINER redis-cli MODULE LIST | grep -i search)
if [ -n "$SEARCH_MODULE" ]; then
    echo "✅ Redis search module is available!"
else
    echo "❌ Redis search module not found!"
    exit 1
fi

# Check if we can create a test vector index
echo "Testing vector index creation..."
INDEX_NAME="test_vector_index"

# Delete test index if it exists
docker exec $CONTAINER redis-cli FT.DROPINDEX $INDEX_NAME 2>/dev/null

# Create a test vector index
docker exec $CONTAINER redis-cli FT.CREATE $INDEX_NAME ON HASH PREFIX 1 "test:" SCHEMA text TEXT doc_id TEXT embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 384 DISTANCE_METRIC COSINE

# Check creation status
if [ $? -eq 0 ]; then
    echo "✅ Successfully created test vector index!"
else
    echo "❌ Failed to create test vector index!"
    exit 1
fi

# Store a few test documents with vectors
echo "Testing vector storage..."

# Function to create a random 384-dimension vector
create_random_vector() {
    # Generate 384 random values between -1 and 1
    for i in {1..384}; do
        echo -n "$(awk -v min=-1 -v max=1 'BEGIN{srand(); print min+rand()*(max-min)}') "
    done
}

# Store test documents with different content
store_test_doc() {
    local id=$1
    local text="$2"
    local vector=$(create_random_vector)
    
    echo "Storing document $id: '$text'"
    docker exec $CONTAINER redis-cli HSET "test:$id" text "$text" doc_id "$id" embedding "$vector"
    
    # Verify storage
    STORED=$(docker exec $CONTAINER redis-cli HGET "test:$id" text)
    if [ "$STORED" == "$text" ]; then
        echo "  ✅ Successfully stored test document $id"
    else
        echo "  ❌ Failed to store test document $id!"
        return 1
    fi
}

# Store some sample documents
store_test_doc "doc1" "Redis vector search is amazing for semantic search applications"
store_test_doc "doc2" "MagicScroll uses Redis to store conversation history"
store_test_doc "doc3" "The vector embeddings help find similar content quickly"
store_test_doc "doc4" "This is a completely unrelated document about cats and dogs"

# Test basic search (will match all documents)
echo "Testing basic search..."
SEARCH_RESULT=$(docker exec $CONTAINER redis-cli FT.SEARCH $INDEX_NAME "*" LIMIT 0 10)
DOC_COUNT=$(echo "$SEARCH_RESULT" | head -n 1)

if [ "$DOC_COUNT" -gt 0 ]; then
    echo "✅ Basic search returned $DOC_COUNT documents!"
else
    echo "❌ Basic search failed!"
    exit 1
fi

# Test KNN search with a test vector (will use first document's vector)
echo "Testing KNN vector search..."
# Get vector from first document
TEST_VECTOR=$(docker exec $CONTAINER redis-cli HGET "test:doc1" embedding)
if [ -z "$TEST_VECTOR" ]; then
    echo "❌ Could not retrieve test vector!"
    exit 1
fi

# Perform KNN search
KNN_RESULT=$(docker exec $CONTAINER redis-cli FT.SEARCH $INDEX_NAME "*=>[KNN 2 @embedding \$vec AS score]" PARAMS 2 vec "$TEST_VECTOR")
KNN_COUNT=$(echo "$KNN_RESULT" | head -n 1)

if [ "$KNN_COUNT" -gt 0 ]; then
    echo "✅ KNN search returned $KNN_COUNT results!"
    # Print results summary
    echo "Search results:"
    echo "$KNN_RESULT" | grep -A 1 "text" | grep -v "text"
else
    echo "❌ KNN search failed!"
    exit 1
fi

# Clean up
echo "Cleaning up test data..."
docker exec $CONTAINER redis-cli DEL test:doc1 test:doc2 test:doc3 test:doc4
docker exec $CONTAINER redis-cli FT.DROPINDEX $INDEX_NAME

echo "🎉 All vector store tests passed! Your Redis vector search is configured correctly."
echo "You can now use ramble with full vector search capabilities!"