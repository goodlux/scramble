"""Enhanced conversation manager with FIPA ACL integration."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, List, Optional, Dict, Any, Union

from scramble.magicscroll.digital_trinity.fipa_acl import FIPAACLMessage
from scramble.utils.logging import get_logger
from .active_conversation import ConversationMessage, ActiveConversation

logger = get_logger(__name__)

class EnhancedConversation(ActiveConversation):
    """Enhanced conversation manager with FIPA ACL support."""
    
    def __init__(self):
        """Initialize conversation state with FIPA support."""
        super().__init__()
        self.fipa_messages: List[FIPAACLMessage] = []
        self.fipa_id_map: Dict[str, FIPAACLMessage] = {}  # Map message.id to FIPA message
    
    async def add_fipa_message(self, message: FIPAACLMessage) -> None:
        """Add a FIPA ACL message to the conversation.
        
        This method adds the FIPA message and also creates a standard
        ConversationMessage for backward compatibility.
        
        Args:
            message: The FIPA ACL message to add
        """
        # Add to FIPA message list
        self.fipa_messages.append(message)
        self.fipa_id_map[message.id] = message
        
        # Create and add compatible ConversationMessage
        conv_message = ConversationMessage(
            content=message.content,
            speaker=message.sender,
            recipient=message.receiver,
            timestamp=datetime.fromisoformat(message.created_at)
        )
        
        # Use the standard method to maintain all the tracking logic
        await self.add_message(
            content=message.content,
            speaker=message.sender,
            recipient=message.receiver
        )
        
        # Update listener states based on performative
        # Different performatives have different implications for state tracking
        if message.performative in ["INFORM", "CONFIRM", "DISCONFIRM"]:
            # These are statements that should update listener state
            for model in self.active_models:
                if model.lower() != message.sender.lower():
                    self.listener_states[model] = datetime.fromisoformat(message.created_at)
        
        # Handle speaker tracking
        if message.sender != "user" and message.sender != "system":
            # For model messages, set as current speaker
            self.current_speaker = message.sender
    
    def get_fipa_history(
        self, 
        limit: Optional[int] = None,
        for_model: Optional[str] = None
    ) -> List[FIPAACLMessage]:
        """Get the FIPA message history.
        
        Args:
            limit: Optional maximum number of messages to return
            for_model: Optional model name to filter relevant messages
            
        Returns:
            List of FIPA ACL messages
        """
        if limit:
            messages = self.fipa_messages[-limit:]
        else:
            messages = self.fipa_messages
        
        # If we're getting history for a specific model, filter out
        # messages the model has already seen
        if for_model and for_model in self.listener_states:
            last_seen = self.listener_states[for_model]
            return [
                msg for msg in messages
                if datetime.fromisoformat(msg.created_at) > last_seen
            ]
        
        return messages
    
    def get_thread_messages(self, message_id: str) -> List[FIPAACLMessage]:
        """Get all messages in a thread (replies to a message).
        
        Args:
            message_id: The ID of the message to get replies for
            
        Returns:
            List of FIPA ACL messages in the thread
        """
        # Start with the original message if available
        thread = []
        if message_id in self.fipa_id_map:
            thread.append(self.fipa_id_map[message_id])
        
        # Find all messages that have in_reply_to matching this message
        for msg in self.fipa_messages:
            if msg.in_reply_to == message_id:
                thread.append(msg)
                
                # Recursively add replies to this message
                if msg.id != message_id:  # Avoid infinite loop
                    thread.extend(self.get_thread_messages(msg.id))
        
        return thread
    
    def format_fipa_conversation(self) -> Dict[str, Any]:
        """Format the conversation with FIPA data for storage.
        
        Returns:
            Dictionary with conversation data
        """
        # Convert FIPA messages to dicts
        fipa_data = [msg.to_dict() for msg in self.fipa_messages]
        
        return {
            "messages": [
                {
                    "speaker": msg.speaker,
                    "recipient": msg.recipient,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in self.messages
            ],
            "fipa_messages": fipa_data,
            "start_time": self.start_time.isoformat(),
            "active_models": list(self.active_models)
        }
    
    def parse_addressed_model(self, message: str) -> tuple[Optional[str], str]:
        """
        Parse message for @model addressing with case-insensitive matching.
        Uses standard implementation with FIPA awareness.
        
        Returns (addressed_model, cleaned_message)
        """
        # Use the standard implementation
        addressed_model, cleaned_message = super().parse_addressed_model(message)
        
        # Additional FIPA-specific processing could be added here
        # For example, if message contains a FIPA performative indicator
        
        return addressed_model, cleaned_message