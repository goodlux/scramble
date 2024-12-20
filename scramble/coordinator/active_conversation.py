"""Manages active conversation sessions."""
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from typing import Set, List, Optional, Dict, Any


@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    content: str
    speaker: str  # 'user' or model name
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ActiveConversation:
    """Represents a live conversation session."""
    
    def __init__(self):
        self.message_queue: asyncio.Queue[ConversationMessage] = asyncio.Queue()
        self.active_models: Set[str] = set()
        self.messages: List[ConversationMessage] = []
        self.current_entry_id: Optional[str] = None  # Links to MSConversation
        self.start_time: datetime = datetime.utcnow()
        
    def add_model(self, model_name: str) -> None:
        """Add a model to the conversation."""
        self.active_models.add(model_name)
        
    def remove_model(self, model_name: str) -> None:
        """Remove a model from the conversation."""
        self.active_models.remove(model_name)
        
    async def add_message(self, content: str, speaker: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation queue."""
        message = ConversationMessage(
            content=content,
            speaker=speaker,
            metadata=metadata or {}
        )
        self.messages.append(message)
        await self.message_queue.put(message)
    
    def format_conversation(self) -> str:
        """Format the conversation for storage."""
        formatted_messages = []
        for msg in self.messages:
            prefix = "User:" if msg.speaker == "user" else f"{msg.speaker}:"
            formatted_messages.append(f"{prefix} {msg.content}")
        return "\n".join(formatted_messages)