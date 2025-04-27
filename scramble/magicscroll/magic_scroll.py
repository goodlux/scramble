"""Core MagicScroll system providing simple storage and search capabilities."""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import os

from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from .ms_entry import MSEntry, EntryType, MSConversation
from .ms_milvus_store import MSMilvusStore
from .ms_types import SearchResult
from .ms_fipa import MSFIPAStorage
from scramble.utils.logging import get_logger
from scramble.config import Config

logger = get_logger(__name__)

class MagicScroll:
    """Core system for storing and searching chat conversations with context enrichment."""
    
    def __init__(self):
        """Initialize with config."""
        self.ms_store = None
        self.search_engine = None
        self.fipa_storage = MSFIPAStorage()

    @classmethod 
    async def create(cls) -> 'MagicScroll':
        """Create a new MagicScroll using global config."""
        magicscroll = cls()
        await magicscroll.initialize()
        return magicscroll
    
    async def initialize(self) -> None:
        """Initialize the components with better error handling."""
        try:
            logger.info("Initializing MagicScroll with Milvus Lite storage...")
            
            # Set up llama-index settings to use local embeddings
            try:
                logger.info("Setting up embedding model...")
                # Use local embedding model with significantly smaller footprint
                embed_model = HuggingFaceEmbedding(
                    model_name="all-MiniLM-L6-v2",  # Much smaller and widely available
                    embed_batch_size=10
                )
                Settings.embed_model = embed_model
                
                # Add node parser for chunking
                Settings.node_parser = SentenceSplitter(
                    chunk_size=1024, 
                    chunk_overlap=50
                )
                
                logger.info("Embedding model loaded successfully")
            except Exception as model_err:
                logger.warning(f"Embedding model load failed: {str(model_err)}")
                logger.warning("Will operate with reduced functionality")
                
                # Set a fallback if needed
                try:
                    from llama_index.embeddings.base import SimilarityMode
                    from llama_index.embeddings.utils import FakeEmbedding
                    
                    # Create a fake embedding model for testing
                    fake_embed = FakeEmbedding(dim=384, similarity_mode=SimilarityMode.EUCLIDEAN)
                    Settings.embed_model = fake_embed
                    logger.info("Using fake embeddings for testing")
                except Exception:
                    pass
                
            # Initialize the Milvus store
            self.ms_store = await MSMilvusStore.create()
            
            # Initialize the search engine
            from .ms_search import MSSearch
            self.search_engine = MSSearch(self)
            
            logger.info("MagicScroll ready to unroll!")
        
        except Exception as e:
            logger.error(f"Failed to initialize MagicScroll: {str(e)}")
            # Create a minimal functional object instead of raising
            self.ms_store = None
            self.search_engine = None
            logger.warning("MagicScroll running in minimal mode")
        
    async def save_ms_entry(self, entry: MSEntry) -> str:
        """Save an entry through the store."""
        if not self.ms_store:
            logger.warning("Cannot save entry - MagicScroll store not initialized")
            return entry.id  # Return ID but don't save

        try:
            if not await self.ms_store.save_ms_entry(entry):
                logger.error("Failed to write entry to store")
                return entry.id  # Return ID even if save failed
            
            logger.info(f"Successfully saved entry {entry.id} to store")
            return entry.id
        except Exception as e:
            logger.error(f"Error saving entry: {e}")
            return entry.id

    async def get_ms_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Get an entry from the store."""
        if not self.ms_store:
            logger.warning("Cannot retrieve entry - MagicScroll store not initialized")
            return None
            
        try:
            entry = await self.ms_store.get_ms_entry(entry_id)
            if entry:
                logger.info(f"Successfully retrieved entry {entry_id}")
            else:
                logger.warning(f"Entry {entry_id} not found in store")
            return entry
        except Exception as e:
            logger.error(f"Error retrieving entry: {e}")
            return None

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search entries in the scroll using vector search."""
        if not self.search_engine:
            logger.warning("Search engine not available")
            return []
            
        try:
            logger.info(f"Searching with query: '{query}', limit={limit}")
            if entry_types:
                logger.info(f"Filtering by entry types: {[t.value for t in entry_types]}")
            if temporal_filter:
                logger.info(f"Filtering by time window: {temporal_filter}")
                
            # Use MSSearch to perform the search
            results = await self.search_engine.search(
                query=query,
                entry_types=entry_types,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            logger.info(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return []

    async def search_conversation(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Search for conversation context using semantic similarity."""
        if not self.search_engine:
            logger.warning("Search engine not available")
            return []
            
        try:
            logger.info(f"Searching for conversation context with: '{message[:50]}...'")
            
            # Use MSSearch's conversation-optimized search
            results = await self.search_engine.conversation_context_search(
                message=message,
                temporal_filter=temporal_filter,
                limit=limit
            )
            
            logger.info(f"Conversation search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in conversation search: {e}")
            return []

    async def get_recent(
        self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        if not self.ms_store or not hasattr(self.ms_store, 'get_recent_entries'):
            logger.warning("Recent entries retrieval not available")
            return []
            
        try:
            entries = await self.ms_store.get_recent_entries(hours, entry_types, limit)
            return entries
        except Exception as e:
            logger.error(f"Error retrieving recent entries: {e}")
            return []

    # FIPA-related methods
    def create_fipa_conversation(self, metadata=None):
        """Create a new FIPA conversation."""
        return self.fipa_storage.create_conversation(metadata)
    
    def save_fipa_message(self, conversation_id, sender, receiver, 
                         content, performative="INFORM", metadata=None):
        """Save a FIPA message."""
        return self.fipa_storage.save_message(
            conversation_id, sender, receiver, content, performative, metadata
        )
    
    def get_fipa_conversation(self, conversation_id, include_ephemeral=False):
        """Get messages from a FIPA conversation."""
        return self.fipa_storage.get_filtered_conversation(
            conversation_id, include_ephemeral
        )
    
    def close_fipa_conversation(self, conversation_id):
        """Close a FIPA conversation."""
        return self.fipa_storage.close_conversation(conversation_id)
        
    async def save_fipa_conversation_to_ms(self, conversation_id, metadata=None):
        """Save filtered FIPA conversation to MagicScroll long-term memory."""
        messages = self.fipa_storage.get_filtered_conversation(conversation_id)
        
        # Format the conversation for storage
        formatted_content = self._format_fipa_conversation(messages)
        
        # Create conversation entry
        entry = MSConversation(
            content=formatted_content,
            metadata={
                "fipa_conversation_id": conversation_id,
                "permanent_message_count": len(messages),
                **(metadata or {})
            }
        )
        
        # Add to the index
        return await self.save_ms_entry(entry)
    
    def _format_fipa_conversation(self, messages):
        """Format FIPA messages into a storable conversation format."""
        formatted = []
        
        for msg in messages:
            sender = msg["sender"]
            content = msg["content"]
            formatted.append(f"{sender}: {content}")
            
        return "\n\n".join(formatted)

    async def close(self) -> None:
        """Close connections."""
        if self.ms_store and hasattr(self.ms_store, 'close'):
            await self.ms_store.close()
            logger.info("MagicScroll connections closed")
