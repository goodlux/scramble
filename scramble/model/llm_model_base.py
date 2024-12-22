"""Base class for Scramble's LLM models."""
from typing import Dict, Any, AsyncGenerator, Union, List, Literal, TypedDict
from datetime import datetime
import asyncio
import time
import logging
from .model_base import ModelBase
from ..core.config_manager import ConfigManager

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
    
    @classmethod
    async def create(cls, model_name: str) -> "LLMModelBase":
        """Create and initialize a new model instance.
        Args:
            model_name: Friendly name/key for the model (e.g., 'sonnet')
        """
        self = cls(model_name)
        await self.initialize()
        return self
    
    def __init__(self, model_name: str):
        """Initialize the model.
        Args:
            model_name: Friendly name/key for the model (e.g., 'sonnet')
        """
        self.model_name = model_name        # 'sonnet'
        self.model_id: str | None = None    # 'claude-3-sonnet-20240229'
        self.config: Dict[str, Any] = {}
        self.rate_limit = 2.0
        self._last_request = 0.0
        
        # Context management - using standardized message format
        self.max_context_length = 4096
        self.context_buffer: List[Message] = []
        self.system_message: str | None = None

    async def initialize(self) -> None:
        """Initialize the model with configuration."""
        config_manager = ConfigManager()
        self.config = await config_manager.get_model_config(self.model_name)
        self.model_id = self.config["model_id"]
        
        # Provider-specific initialization
        await self._initialize_client()
        if not self.validate_config():
            raise ValueError("Invalid configuration")
            
        # Provider-specific initialization
        await self._initialize_client()

    async def _initialize_client(self) -> None:
        """Initialize provider-specific client. Must be implemented by subclasses."""
        raise NotImplementedError


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