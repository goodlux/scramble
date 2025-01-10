# ms_entry.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
import uuid

class EntryType(Enum):
    """Types of entries that can be stored in the MagicScroll."""
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    IMAGE = "image"
    CODE = "code"
    TOOL_CALL = "tool_call"

@dataclass
class MSEntry:
    """Base class for all MagicScroll entries."""
    content: str
    entry_type: EntryType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None

    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary format."""
        base_dict = {
            "id": self.id,
            "content": self.content,
            "type": self.entry_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        # Only include parent_id if it exists
        if self.parent_id is not None:
            base_dict["parent_id"] = self.parent_id
            
        return base_dict
    
    @staticmethod
    def sanitize_metadata_for_chroma(metadata: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
        """Convert metadata values to ChromaDB compatible types."""
        if metadata is None:
            return {}
            
        sanitized = {}
        for key, value in metadata.items():
            # Skip None values
            if value is None:
                continue
                
            # Convert datetime to ISO string
            if isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            # Convert basic types
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            # Convert dict to string (for nested metadata)
            elif isinstance(value, dict):
                sanitized[key] = str(value)
            # Convert list to string
            elif isinstance(value, list):
                sanitized[key] = str(value)
            # Convert any other type to string
            else:
                sanitized[key] = str(value)
                
        return sanitized

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MSEntry':
        """Create entry from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            entry_type=EntryType(data["type"]),
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            parent_id=data.get("parent_id")  # Use get() to handle missing parent_id
        )

class MSConversation(MSEntry):
    """Represents a conversation entry."""
    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        entry_id: Optional[str] = None
    ):
        super().__init__(
            id=entry_id or str(uuid.uuid4()),
            content=content,
            entry_type=EntryType.CONVERSATION,
            metadata={
                **(metadata or {}),
                "speaker_count": content.count("Assistant:") + content.count("User:")
            },
            parent_id=parent_id
        )

class MSDocument(MSEntry):
    """Represents a document entry."""
    def __init__(
        self,
        title: str,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None
    ):
        super().__init__(
            id=entry_id or str(uuid.uuid4()),
            content=f"{title}\n\n{content}",
            entry_type=EntryType.DOCUMENT,
            metadata={
                **(metadata or {}),
                "title": title,
                "uri": uri
            }
        )

class MSImage(MSEntry):
    """Represents an image entry."""
    def __init__(
        self,
        caption: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None
    ):
        super().__init__(
            id=entry_id or str(uuid.uuid4()),
            content=caption,
            entry_type=EntryType.IMAGE,
            metadata={
                **(metadata or {}),
                "uri": uri
            }
        )

class MSCode(MSEntry):
    """Represents a code entry."""
    def __init__(
        self,
        code: str,
        language: str,
        metadata: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None
    ):
        super().__init__(
            id=entry_id or str(uuid.uuid4()),
            content=code,
            entry_type=EntryType.CODE,
            metadata={
                **(metadata or {}),
                "language": language
            }
        )