"""Manages active conversation sessions."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, List, Optional, Dict, Any

@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    content: str
    speaker: str  # 'user', 'system', or model_name
    recipient: Optional[str] = None  # Who the message is addressed to
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ActiveConversation:
    """Represents a live conversation session."""
    
    def __init__(self):
        """Initialize conversation state."""
        self.active_models: Set[str] = set()
        self.messages: List[ConversationMessage] = []
        self.start_time: datetime = datetime.utcnow()
        
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
    
    def get_last_n_messages(self, n: int) -> List[ConversationMessage]:
        """Get the last n messages from the conversation."""
        return self.messages[-n:] if self.messages else []

    def get_messages_since(self, timestamp: datetime) -> List[ConversationMessage]:
        """Get all messages since a specific timestamp."""
        return [msg for msg in self.messages if msg.timestamp > timestamp]

    async def add_message(self, content: str, speaker: str, recipient: Optional[str] = None) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(
            content=content,
            speaker=speaker,
            recipient=recipient,
        )
        self.messages.append(message)
        
        # Update listener states when a message is added
        if speaker != "user" and speaker != "system":
            for model in self.active_models:
                if model.lower() != speaker.lower():  # Case-insensitive comparison
                    self.listener_states[model] = message.timestamp

    def format_conversation(self) -> str:
        """Format the conversation for storage."""
        formatted_messages = []
        for msg in self.messages:
            # Just use the speaker name directly - it's already what we want
            prefix = "User" if msg.speaker == "user" else msg.speaker.capitalize()
            if msg.recipient:
                formatted_messages.append(f"{prefix} to {msg.recipient}: {msg.content}")
            else:
                formatted_messages.append(f"{prefix}: {msg.content}")
        return "\n".join(formatted_messages)

    def format_conversation_for_storage(self) -> Dict[str, Any]:
        """Format conversation for storage with metadata."""
        formatted_messages = []
        
        for msg in self.messages:
            formatted_msg = {
                "speaker": msg.speaker,
                "recipient": msg.recipient,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            formatted_messages.append(formatted_msg)
                
        return {
            "messages": formatted_messages,
            "start_time": self.start_time.isoformat(),
            "active_models": list(self.active_models)
        }