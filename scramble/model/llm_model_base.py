"""Base class for Scramble's LLM models."""
from typing import Dict, Any, AsyncGenerator, Union, List, Literal, TypedDict
from datetime import datetime
import asyncio
import time
import logging
from .model_base import ModelBase
from ..model_config.config_manager import ConfigManager 
from abc import ABC, abstractmethod

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
    
    # Declare class attributes with types
    model_name: str
    model_id: str | None
    config: Dict[str, Any]
    rate_limit: float
    _last_request: float
    max_context_length: int
    context_buffer: List[Message]
    system_message: str | None
    
    @classmethod
    async def create(cls, model_name: str) -> "LLMModelBase":
        """Create and initialize a new model instance.
        Args:
            model_name: Friendly name/key for the model (e.g., 'sonnet')
        """
        self = cls()  # Create uninitialized instance
        
        # Basic setup
        self.model_name = model_name
        self.model_id = None
        self.config = {}
        self.rate_limit = 2.0
        self._last_request = 0.0
        self.max_context_length = 4096
        self.context_buffer = []
        self.system_message = None
        
        # Load config and initialize client
        try:
            config_manager = ConfigManager()
            self.config = await config_manager.get_model_config(self.model_name)
            self.model_id = self.config["model_id"]
            await self._initialize_client()
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise
            
        return self

    def __init__(self):
        """Basic initialization only. Use create() instead."""
        pass  # All initialization happens in create()

    @abstractmethod
    async def _initialize_client(self) -> None:
        """Initialize provider-specific client. Must be implemented by subclasses."""
        raise NotImplementedError

    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs: Any) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response from the model.
        
        Args:
            prompt: The input text to generate a response for
            **kwargs: Additional model-specific parameters
            
        Returns:
            Either a string response or an async generator for streaming responses
        """
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