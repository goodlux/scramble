# magic_scroll.py
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
from .ms_entry import (
    MSEntry, 
    MSConversation, 
    MSDocument, 
    MSImage, 
    MSCode,
    EntryType
)
from .ms_index import MSIndexBase, LlamaIndexImpl
from .ms_store import RedisStore
import redis
from llama_index.core import Document
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

logger = logging.getLogger(__name__)

class MagicScroll:
    """
    THE scroll that rules them all.
    
    A unified, personal store of all conversations and knowledge.
    - Conversations with AI
    - Documents and their contents
    - Images and their descriptions
    - Code snippets and their context
    - Tool interactions and their results
    
    Everything is searchable, connected, and yours.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the one true scroll."""
        self.storage_path = storage_path or Path.home() / '.scramble' / 'scroll'
        logger.info(f"Initializing MagicScroll at {self.storage_path}")
        
        # Initialize the index
        self.doc_store = RedisStore()
        self.index = LlamaIndexImpl(self.storage_path)
    
    async def write_conversation(self,
        content: str,
        metadata: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Write a conversation to the scroll."""
        entry = MSConversation(
            content=content,
            metadata={"tags": metadata} if metadata else None,
            parent_id=parent_id
        )
        
        try:
            # Store in both Redis and vector index
            doc = Document(
                text=entry.content,
                doc_id=entry.id,
            )
            
            # Store in both stores via storage context
            if await self.index.add_entry(entry):
                logger.info(f"Added conversation entry {entry.id}")
                return entry.id
            else:
                raise RuntimeError("Failed to write conversation to scroll")
                
        except Exception as e:
            logger.error(f"Error writing conversation: {str(e)}")
            raise RuntimeError(f"Failed to write conversation to scroll: {str(e)}")
        
    
    async def write_document(self,
        title: str,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write a document to the scroll.
        
        Args:
            title: Document title
            content: Document content
            uri: Where the document is stored
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
        entry = MSDocument(
            title=title,
            content=content,
            uri=uri,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added document entry {entry.id}: {title}")
            return entry.id
        else:
            raise RuntimeError("Failed to write document to scroll")
    
    async def write_image(self,
        caption: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write an image to the scroll.
        
        Args:
            caption: Image description
            uri: Where the image is stored
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
        entry = MSImage(
            caption=caption,
            uri=uri,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added image entry {entry.id}")
            return entry.id
        else:
            raise RuntimeError("Failed to write image to scroll")
    
    async def write_code(self,
        code: str,
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write code to the scroll.
        
        Args:
            code: The code content
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            The ID of the new entry
        """
        entry = MSCode(
            code=code,
            language=language,
            metadata=metadata
        )
        
        if await self.index.add_entry(entry):
            logger.info(f"Added code entry {entry.id} [{language}]")
            return entry.id
        else:
            raise RuntimeError("Failed to write code to scroll")
    
    async def remember(self, query: str, entry_types: Optional[List[EntryType]] = None,
                      limit: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Search the scroll's memory."""
        # Search vector index
        results = await self.index.search(query, entry_types, limit, min_score)
        
        # Fetch full entries from Redis
        enhanced_results = []
        for result in results:
            entry_id = result["entry"].id
            full_entry = await self.doc_store.get_entry(entry_id)
            if full_entry:
                result["entry"] = full_entry
                enhanced_results.append(result)
        
        return enhanced_results
    
    async def recall(self, entry_id: str) -> Optional[MSEntry]:
        """
        Recall a specific entry from the scroll.
        
        Args:
            entry_id: The ID of the entry to recall
            
        Returns:
            The entry if found, None otherwise
        """
        return await self.index.get_entry(entry_id)
    
    async def forget(self, entry_id: str) -> bool:
        """
        Remove an entry from the scroll.
        
        Args:
            entry_id: The ID of the entry to forget
            
        Returns:
            True if successfully forgotten
        """
        return await self.index.delete_entry(entry_id)
    
    async def recall_recent(self,
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """
        Recall recent entries from the scroll.
        
        Args:
            hours: Optional time window
            entry_types: Optional types to filter
            limit: Maximum number of entries
            
        Returns:
            List of recent entries
        """
        return await self.index.get_recent(hours, entry_types, limit)
    
    async def recall_thread(self, entry_id: str) -> List[MSEntry]:
        """
        Recall a complete thread of entries.
        
        Args:
            entry_id: Any entry ID in the thread
            
        Returns:
            List of entries in chronological order
        """
        return await self.index.get_chain(entry_id)
    
    async def summarize(self) -> Dict[str, Any]:
        """Get a summary of the scroll's contents."""
        recent = await self.recall_recent(hours=24)
        types = {}
        for entry in recent:
            types[entry.entry_type.value] = types.get(entry.entry_type.value, 0) + 1
            
        return {
            "recent_24h": len(recent),
            "entry_types": types,
            "latest_entry": recent[0].created_at if recent else None
        }