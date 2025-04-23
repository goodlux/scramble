#!/usr/bin/env python
"""
Test script for MagicScroll vector search functionality.
This tool helps verify that the vector search is working correctly.
"""
import os
import sys
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path setup
from scramble.magicscroll.magic_scroll import MagicScroll
from scramble.magicscroll.ms_entry import MSEntry, EntryType
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

async def create_test_entries():
    """Create some test entries for vector search testing."""
    logger.info("Creating test entries for vector search...")
    
    # Initialize MagicScroll
    scroll = await MagicScroll.create()
    
    if not scroll or not hasattr(scroll, 'store') or not scroll.store:
        logger.error("Failed to initialize MagicScroll storage")
        return False
    
    # Sample test entries
    test_entries = [
        {
            "content": "Redis vector search enables semantic similarity search in MagicScroll",
            "type": EntryType.CONVERSATION,
            "metadata": {"test_group": "vector_search", "topic": "redis"}
        },
        {
            "content": "The implementation uses LlamaIndex with Redis as the vector store",
            "type": EntryType.CONVERSATION,
            "metadata": {"test_group": "vector_search", "topic": "implementation"}
        },
        {
            "content": "Embeddings are generated using the all-MiniLM-L6-v2 model",
            "type": EntryType.CONVERSATION,
            "metadata": {"test_group": "vector_search", "topic": "embeddings"}
        },
        {
            "content": "Docker containers make it easy to run Redis with the search module",
            "type": EntryType.CONVERSATION,
            "metadata": {"test_group": "vector_search", "topic": "docker"}
        },
        {
            "content": "This is a completely unrelated entry about cats and dogs",
            "type": EntryType.CONVERSATION,
            "metadata": {"test_group": "vector_search", "topic": "unrelated"}
        }
    ]
    
    # Create and store entries
    created_count = 0
    for entry_data in test_entries:
        try:
            # Create entry with slightly different timestamps
            entry = MSEntry(
                content=entry_data["content"],
                entry_type=entry_data["type"],
                metadata=entry_data["metadata"],
                timestamp=datetime.utcnow() - timedelta(minutes=created_count)  # Space them out in time
            )
            
            # Store entry
            success = await scroll.store.save_ms_entry(entry)
            if success:
                created_count += 1
                logger.info(f"Created test entry: {entry.id}")
            else:
                logger.error(f"Failed to create test entry")
                
        except Exception as e:
            logger.error(f"Error creating test entry: {e}")
    
    logger.info(f"Created {created_count} test entries")
    return created_count > 0

async def test_vector_search():
    """Test vector search functionality."""
    logger.info("Testing vector search...")
    
    # Initialize MagicScroll
    scroll = await MagicScroll.create()
    
    if not scroll:
        logger.error("Failed to initialize MagicScroll")
        return False
    
    # Define test queries
    test_queries = [
        "semantic search with Redis",
        "embedding models for vectors",
        "pets and animals",
        "LlamaIndex implementation"
    ]
    
    # Run search tests
    success = True
    for query in test_queries:
        try:
            logger.info(f"\nTesting search query: '{query}'")
            
            # Perform vector search
            results = await scroll.search(
                query=query,
                entry_types=[EntryType.CONVERSATION],
                limit=3
            )
            
            logger.info(f"Found {len(results)} results")
            
            # Display results
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}:")
                logger.info(f"  Score: {result.score:.4f}")
                logger.info(f"  Content: {result.entry.content}")
                logger.info(f"  Topic: {result.entry.metadata.get('topic', 'unknown')}")
                logger.info(f"  Time: {result.entry.timestamp}")
                logger.info("-" * 40)
            
            if not results:
                logger.warning(f"No results found for query: '{query}'")
                success = False
                
        except Exception as e:
            logger.error(f"Error testing search: {e}")
            success = False
    
    return success

async def test_temporal_search():
    """Test temporal search functionality."""
    logger.info("\nTesting temporal search...")
    
    # Initialize MagicScroll
    scroll = await MagicScroll.create()
    
    if not scroll:
        logger.error("Failed to initialize MagicScroll")
        return False
    
    try:
        # Define temporal filter - last 30 minutes
        now = datetime.utcnow()
        temporal_filter = {
            'start': now - timedelta(minutes=30),
            'end': now
        }
        
        logger.info(f"Temporal filter: {temporal_filter['start']} to {temporal_filter['end']}")
        
        # Perform search with temporal filter
        results = await scroll.search(
            query="",  # Empty query to match all entries in the timeframe
            entry_types=[EntryType.CONVERSATION],
            temporal_filter=temporal_filter,
            limit=10
        )
        
        logger.info(f"Found {len(results)} results in time period")
        
        # Display results
        for i, result in enumerate(results):
            logger.info(f"Result {i+1}:")
            logger.info(f"  Time: {result.entry.timestamp}")
            logger.info(f"  Content: {result.entry.content}")
            logger.info("-" * 40)
        
        return len(results) > 0
        
    except Exception as e:
        logger.error(f"Error testing temporal search: {e}")
        return False

async def test_context_search():
    """Test conversation context search functionality."""
    logger.info("\nTesting conversation context search...")
    
    # Initialize MagicScroll
    scroll = await MagicScroll.create()
    
    if not scroll:
        logger.error("Failed to initialize MagicScroll")
        return False
    
    try:
        # Test message for context search
        test_message = "Tell me more about how vector search works with Redis and embeddings"
        logger.info(f"Context search message: '{test_message}'")
        
        # Perform conversation context search
        results = await scroll.search_conversation(
            message=test_message,
            limit=3
        )
        
        logger.info(f"Found {len(results)} context results")
        
        # Display results
        for i, result in enumerate(results):
            logger.info(f"Result {i+1}:")
            logger.info(f"  Score: {result.score:.4f}")
            logger.info(f"  Content: {result.entry.content}")
            logger.info("-" * 40)
        
        return len(results) > 0
        
    except Exception as e:
        logger.error(f"Error testing context search: {e}")
        return False

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MagicScroll vector search")
    parser.add_argument('--create', action='store_true', help="Create test entries")
    parser.add_argument('--vector', action='store_true', help="Test vector search")
    parser.add_argument('--temporal', action='store_true', help="Test temporal search")
    parser.add_argument('--context', action='store_true', help="Test conversation context search")
    parser.add_argument('--all', action='store_true', help="Run all tests")
    
    args = parser.parse_args()
    
    # Run all tests if --all is specified
    if args.all:
        args.create = args.vector = args.temporal = args.context = True
    
    # Create test entries if requested
    if args.create:
        await create_test_entries()
    
    # Run the tests
    if args.vector:
        await test_vector_search()
        
    if args.temporal:
        await test_temporal_search()
        
    if args.context:
        await test_context_search()
    
    if not any([args.create, args.vector, args.temporal, args.context]):
        print("Error: Please specify test options")
        print("Example: python test_vector_search.py --all")
        print("Example: python test_vector_search.py --create --vector")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())