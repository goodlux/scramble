"""Domain types for MagicScroll."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import uuid

from llama_index.core import Document

class EntryType(Enum):
    """Types of entries in MagicScroll."""
    CONVERSATION = "conversation"
    DOCUMENT = "document"  # For PDFs, text files, etc
    IMAGE = "image"        # For image files
    CODE = "code"         # For code snippets/files

@dataclass
class MSEntry:
    """Base class for MagicScroll entries."""
    content: str
    entry_type: EntryType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_document(self) -> Document:
        """Convert entry to LlamaIndex Document for storage/indexing."""
        return Document(
            text=self.content,
            doc_id=self.id,
            metadata={
                "type": self.entry_type.value,
                "created_at": self.created_at.isoformat(),
                **self.metadata
            }
        )

    @classmethod
    def from_document(cls, doc: Document) -> 'MSEntry':
        """Create entry from LlamaIndex Document.
        
        Note: This assumes the document was created from an MSEntry.
        It reconstructs the original entry type from metadata.
        """
        metadata = doc.metadata or {}
        entry_type = metadata.get("type", "conversation")
        
        # Remove the fields we store separately
        clean_metadata = {k: v for k, v in metadata.items() 
                         if k not in ["type", "created_at"]}
        
        # Parse created_at back to datetime, default to now if not found
        created_at = metadata.get("created_at")
        if created_at:
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.utcnow()

        return cls(
            id=doc.doc_id,
            content=doc.text,
            entry_type=EntryType(entry_type),
            metadata=clean_metadata,
            created_at=created_at
        )

class MSConversation(MSEntry):
    """A conversation entry - fully implemented."""
    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            content=content,
            entry_type=EntryType.CONVERSATION,
            metadata={
                **(metadata or {}),
                "speaker_count": content.count("Assistant:") + content.count("User:")
            }
        )

class MSDocument(MSEntry):
    """
    A document entry (PDF, text, etc) - NOT YET IMPLEMENTED.
    Will require appropriate LlamaIndex Reader (PDFReader, etc)
    to convert to text before storage.
    """
    def __init__(self):
        raise NotImplementedError(
            "Document handling not yet implemented. "
            "Will require LlamaIndex Reader setup."
        )

class MSImage(MSEntry):
    """
    An image entry - NOT YET IMPLEMENTED.
    Will require ImageReader or similar to extract/generate 
    text content before storage.
    """
    def __init__(self):
        raise NotImplementedError(
            "Image handling not yet implemented. "
            "Will require image processing setup."
        )

class MSCode(MSEntry):
    """
    A code entry - NOT YET IMPLEMENTED.
    May require special handling for language-specific parsing
    or documentation extraction.
    """
    def __init__(self):
        raise NotImplementedError(
            "Code handling not yet implemented. "
            "Will require code parsing setup."
        )