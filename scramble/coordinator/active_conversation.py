"""Manages active conversation sessions."""
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from typing import Set, List, Optional, Dict, Any
from .temporal_processor import TemporalProcessor, TemporalReference

@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    content: str
    speaker: str  # 'user' or model_name (e.g., 'phi4', 'sonnet')
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    temporal_references: List[TemporalReference] = field(default_factory=list)

class ActiveConversation:
    """Represents a live conversation session."""
    
    def __init__(self):
        self.message_queue: asyncio.Queue[ConversationMessage] = asyncio.Queue()
        self.active_models: Set[str] = set()
        self.messages: List[ConversationMessage] = []
        self.current_entry_id: Optional[str] = None  # Links to MSConversation
        self.start_time: datetime = datetime.utcnow()
        self.temporal_processor = TemporalProcessor()
        
        # Dialogue state handling
        self.current_speaker: Optional[str] = None
        self.listener_states: Dict[str, datetime] = {}
        
    def add_model(self, model_name: str) -> None:
        """Add a model to the conversation."""
        self.active_models.add(model_name)
        self.listener_states[model_name] = datetime.utcnow()
        
    def remove_model(self, model_name: str) -> None:
        """Remove a model from the conversation."""
        self.active_models.remove(model_name)
        if model_name in self.listener_states:
            del self.listener_states[model_name]
        if self.current_speaker == model_name:
            self.current_speaker = None

    def parse_addressed_model(self, message: str) -> tuple[Optional[str], str]:
        """
        Parse message for @model addressing with case-insensitive matching.
        Returns (addressed_model, cleaned_message)
        """
        words = message.split()
        if not words:
            return None, message
            
        if words[0].startswith('@'):
            model_name = words[0][1:].lower()  # Convert to lowercase for comparison
            # Case-insensitive model name lookup
            for active_model in self.active_models:
                if active_model.lower() == model_name:
                    self.current_speaker = active_model  # Use the correct case from active_models
                    return active_model, ' '.join(words[1:])
                
        return self.current_speaker, message

    def should_model_respond(self, model_name: str) -> bool:
        """Determine if a model should respond based on conversation state."""
        if len(self.active_models) == 1:
            return True
        return model_name.lower() == self.current_speaker.lower() if self.current_speaker else False

    def get_context_for_model(self, model_name: str) -> Optional[List[ConversationMessage]]:
        """Get any missed context for a model."""
        if model_name not in self.listener_states:
            return None
            
        last_seen = self.listener_states[model_name]
        return [msg for msg in self.messages if msg.timestamp > last_seen]

    async def add_message(self, content: str, speaker: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation queue with temporal processing."""
        # Process temporal references for user messages
        temporal_refs = []
        if speaker == "user":
            temporal_refs = self.temporal_processor.parse_temporal_references(content)

        message = ConversationMessage(
            content=content,
            speaker=speaker,
            metadata=metadata or {},
            temporal_references=temporal_refs
        )
        self.messages.append(message)
        await self.message_queue.put(message)
        
        # Update listener states when a message is added
        if speaker != "user":
            for model in self.active_models:
                if model.lower() != speaker.lower():  # Case-insensitive comparison
                    self.listener_states[model] = message.timestamp

    def get_temporal_context(self) -> List[TemporalReference]:
        """Get temporal context from conversation history."""
        temporal_context = []
        for msg in self.messages:
            if msg.temporal_references:
                temporal_context.extend(msg.temporal_references)
        return temporal_context

    def format_conversation(self) -> str:
        """Format the conversation for storage."""
        formatted_messages = []
        for msg in self.messages:
            # Just use the speaker name directly - it's already what we want
            prefix = "User" if msg.speaker == "user" else msg.speaker.capitalize()
            formatted_messages.append(f"{prefix}: {msg.content}")
        return "\n".join(formatted_messages)

    def format_conversation_with_temporal(self) -> Dict[str, Any]:
        """Format conversation with temporal metadata for storage."""
        formatted_messages = []
        temporal_refs = []
        
        for msg in self.messages:
            formatted_msg = {
                "speaker": msg.speaker,  # Already the clean model_name
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "temporal_references": msg.temporal_references,
                "metadata": msg.metadata
            }
            formatted_messages.append(formatted_msg)
            if msg.temporal_references:
                temporal_refs.extend(msg.temporal_references)
                
        return {
            "messages": formatted_messages,
            "temporal_context": temporal_refs,
            "start_time": self.start_time.isoformat(),
            "active_models": list(self.active_models)
        }