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

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata dictionary without content."""
        return {
            "id": self.id,
            "type": self.entry_type.value,
            "created_at": self.created_at.isoformat(),
            **self.metadata  # spread any additional metadata
        }


    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary format."""
        return {
            "id": self.id,
            "content": self.content,
            "type": self.entry_type.value,
            "created_at": self.created_at.isoformat(),
            **self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MSEntry':
        """Create entry from dictionary format."""
        # Convert created_at from ISO string to datetime
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.utcnow()

        # Extract core fields
        entry_type = data.get("type", "conversation")
        
        # Extract metadata (excluding core fields)
        metadata = {k: v for k, v in data.items() 
                if k not in ['id', 'content', 'type', 'created_at']}

        return cls(
            id=data["id"],
            content=data["content"],
            entry_type=EntryType(entry_type),
            metadata=metadata,
            created_at=created_at
        )

    @classmethod 
    def from_neo4j(cls, node: Any) -> 'MSEntry':
        """Create entry from Neo4j node.
        
        Note: The node parameter is typed as Any to avoid circular imports,
        but it should be a neo4j.graph.Node.
        """
        props = dict(node)
        
        # Convert Neo4j datetime to Python datetime
        created_at = props.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.utcnow()
            
        # Get entry type, default to conversation
        entry_type = props.get('type', 'conversation')

        # Extract metadata (all props except the core ones)
        metadata = {k: v for k, v in props.items() 
                   if k not in ['id', 'content', 'type', 'created_at']}

        return cls(
            id=props['id'],
            content=props['content'],
            entry_type=EntryType(entry_type),
            metadata=metadata,
            created_at=created_at
        )
    
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