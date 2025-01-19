"""Core MagicScroll system providing simple storage and search capabilities."""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Local imports
from .ms_entry import MSEntry, EntryType
from .ms_index import MSIndex
from .ms_search import MSSearch, SearchResult
from scramble.utils.logging import get_logger
from scramble.config import Config

logger = get_logger(__name__)

class MagicScroll:
    def __init__(self, config: Config):
        """Initialize with config."""
        self.index: Optional[MSIndex] = None  # Will be set in create()
        self.config = config
        
    @classmethod 
    async def create(cls) -> 'MagicScroll':
        """Create a new MagicScroll using global config."""
        from scramble.config import config  # Import the global config instance
        magicscroll = cls(config)
        await magicscroll.initialize()
        return magicscroll
    
    async def initialize(self) -> None:
        """Initialize the components."""
        try:
            # Initialize index which handles both storage and search
            self.index = await MSIndex.create(
                self.config.NEO4J_URI,
                auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
            )
            
            logger.info("MagicScroll ready to roll!")
        except Exception as e:
            logger.error(f"Failed to initialize MagicScroll: {str(e)}")
            raise RuntimeError(f"Failed to initialize: {str(e)}")

    async def write_conversation(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Write a conversation entry."""
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        entry = MSEntry(
            content=content,
            entry_type=EntryType.CONVERSATION,
            metadata=metadata
        )
        
        if not await self.index.add_entry(entry):
            raise RuntimeError("Failed to write entry")
            
        return entry.id

    async def read(self, entry_id: str) -> Optional[MSEntry]:
        """Read an entry from the scroll."""
        if not self.index:
            return None
        return await self.index.get_entry(entry_id)

    async def search(
        self,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search entries in the scroll."""
        if not self.index:
            return []
        return await self.index.search(
            query=query,
            entry_types=entry_types,
            temporal_filter=temporal_filter,
            limit=limit
        )

    async def search_conversation(
        self,
        message: str,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        limit: int = 3
    ) -> List[SearchResult]:
        """Search for conversation context."""
        if not self.index:
            return []
        return await self.index.search_conversation(
            message=message,
            temporal_filter=temporal_filter,
            limit=limit
        )

    async def get_recent(
        self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries."""
        if not self.index:
            return []
        return await self.index.get_recent(
            hours=hours,
            entry_types=entry_types,
            limit=limit
        )

    async def close(self) -> None:
        """Close connections."""
        if self.index:
            await self.index.close()