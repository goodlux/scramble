"""Base class for Scramble's LLM models."""
from typing import Dict, Any, AsyncGenerator, Union, List, Literal, TypedDict, Optional
from datetime import datetime
import asyncio
import time
import logging
from abc import ABC, abstractmethod
from .model_base import ModelBase
from ..model_config.config_manager import ConfigManager 

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
    
    def __init__(self):
        """Basic initialization only. Use create() instead."""
        super().__init__()
        # Initialize all class attributes
        self.model_name = ""
        self.model_id = None
        self.config = {}
        self.rate_limit = 2.0
        self._last_request = 0.0
        self.max_context_length = 4096
        self.context_buffer = []
        self.system_message = None

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

    @classmethod
    async def create(cls, model_name: str) -> "LLMModelBase":
        """Create and initialize a new model instance."""
        self = cls()
        
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
            
            # Set system prompt if available in config
            self.system_message = self.config.get("system_prompt")
            if self.system_message:
                logger.info(f"Loaded system prompt for {model_name}")
            
            await self._initialize_client()
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise
            
        return self

    def _add_to_context(
        self,
        role: Role,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
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

    @abstractmethod
    async def _initialize_client(self) -> None:
        """Initialize provider-specific client."""
        raise NotImplementedError

    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs: Any) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response from the model."""
        raise NotImplementedError