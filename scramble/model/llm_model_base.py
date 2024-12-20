"""Base class for Scramble's LLM models."""
from typing import Dict, Any, AsyncGenerator, Union, List, Literal, TypedDict
from datetime import datetime
import asyncio
import time
import logging
from .model_base import ModelBase

logger = logging.getLogger(__name__)

# Type definitions for message handling
Role = Literal["user", "assistant", "system"]

class Message(TypedDict):
    """Type for standardized message format."""
    role: Role
    content: str
    timestamp: str
    metadata: Dict[str, Any]

class LLMModelBase(ModelBase):
    """Base class adding Scramble-specific features to LLM models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the model with configuration."""
        if not config or "model" not in config:
            raise ValueError("Model configuration must include model name")
            
        self.model_name = config["model"]
        self.config = config
        self.rate_limit = config.get("rate_limit", 2.0)
        self._last_request = 0.0
        
        # Context management - using standardized message format
        self.max_context_length = config.get("max_context_length", 4096)
        self.context_buffer: List[Message] = []
        self.system_message: str | None = config.get("system_message")

    # ... rest of the implementation stays the same ...

    def _add_to_context(
        self,
        role: Role,  # Now properly typed
        content: str,
        metadata: Dict[str, Any] | None = None
    ) -> None:
        """Add a message to the context buffer."""
        message: Message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.context_buffer.append(message)
        self._trim_context_if_needed()

    def _trim_context_if_needed(self) -> None:
        """Trim context buffer if it exceeds max length."""
        max_messages = self.config.get("max_context_messages", 10)
        if len(self.context_buffer) > max_messages:
            if self.system_message:
                system_message: Message = {
                    "role": "system",
                    "content": self.system_message,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {}
                }
                self.context_buffer = (
                    [system_message] +
                    self.context_buffer[-(max_messages-1):]
                )
            else:
                self.context_buffer = self.context_buffer[-max_messages:]

    def _format_context_for_provider(self) -> List[Dict[str, str]]:
        """Format context buffer for provider API.
        
        Returns list of messages in standard format:
        [{"role": "user", "content": "..."}, ...]
        """
        messages: List[Dict[str, str]] = []
        
        if self.system_message:
            messages.append({
                "role": "system",
                "content": self.system_message
            })
        
        for msg in self.context_buffer:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        return messages