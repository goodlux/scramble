"""Core MagicScroll system providing simple storage and search capabilities."""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

from .ms_entry import MSEntry, EntryType
from .ms_store import MSStore
from .ms_types import SearchResult
from scramble.utils.logging import get_logger
from scramble.config import Config

logger = get_logger(__name__)

class MagicScroll:
    def __init__(self):
        """Initialize with config."""
        self.ms_store: Optional[MSStore] = None

    @classmethod 
    async def create(cls) -> 'MagicScroll':
        """Create a new MagicScroll using global config."""
        magicscroll = cls()
        await magicscroll.initialize()
        return magicscroll
    
    async def initialize(self) -> None:
        """Initialize the components with better error handling."""
        try:
            logger.info("Initializing MagicScroll with minimal requirements...")
            
            # First set up llama-index settings to use local embeddings
            try:
                logger.info("Setting up embedding model (local mode)...")
                # Use local embedding model with significantly smaller footprint
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                
                # Use a simpler model that's less likely to fail
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
                
                # Set a fallback
                try:
                    from llama_index.embeddings.base import SimilarityMode
                    from llama_index.embeddings.utils import FakeEmbedding
                    
                    # Create a fake embedding model for testing
                    fake_embed = FakeEmbedding(dim=384, similarity_mode=SimilarityMode.EUCLIDEAN)
                    Settings.embed_model = fake_embed
                    logger.info("Using fake embeddings for testing")
                except Exception:
                    pass
                
            # Try to connect to the store after embedding setup
            self.ms_store = await MSStore.create()
            
            # We'll defer loading the LLM until needed
            # This is often what causes the long hangs
            logger.info("Deferred loading of LLM model until needed")
            
            logger.info("MagicScroll ready to unroll!")
        
        except Exception as e:
            logger.error(f"Failed to initialize MagicScroll: {str(e)}")
            # Create a minimal functional object instead of raising
            self.ms_store = None
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
        """Search entries in the scroll."""
        # TODO: Implement search through MSStore
        logger.info("Search not yet implemented")
        return []

    async def search_conversation(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Search for conversation context."""
        # TODO: Implement conversation search through MSStore
        logger.info("Conversation search not yet implemented")
        return []

    async def get_recent(
        self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        # TODO: Implement recent entries retrieval through MSStore
        logger.info("Recent entries retrieval not yet implemented")
        return []

    async def close(self) -> None:
        """Close connections."""
        # TODO: Make a close method in MSStore
        # if self.ms_store:
        #     await self.ms_store.close()