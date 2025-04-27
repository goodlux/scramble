"""FIPA ACL support for LLM models."""
from typing import Dict, List, Any, Optional, Union, Tuple, Protocol, runtime_checkable
import json

from scramble.utils.logging import get_logger

logger = get_logger(__name__)

@runtime_checkable
class FIPAModelSupport(Protocol):
    """Protocol for models that support FIPA ACL messaging."""
    
    supports_fipa: bool = True
    
    def set_message_history(self, messages: List[Dict[str, Any]]) -> None:
        """Set message history from FIPA-converted messages."""
        ...
    
    def clear_message_history(self) -> None:
        """Clear message history."""
        ...
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get current message history."""
        ...

class FIPAModelMixin:
    """Mixin class to add FIPA message support to LLM models."""
    
    supports_fipa = True
    
    def __init__(self, *args, **kwargs):
        """Initialize with empty message history."""
        super().__init__(*args, **kwargs)
        self._message_history: List[Dict[str, Any]] = []
    
    def set_message_history(self, messages: List[Dict[str, Any]]) -> None:
        """Set message history from FIPA-converted messages.
        
        Args:
            messages: List of messages in the model's native format
        """
        self._message_history = messages
        logger.info(f"Set message history with {len(messages)} messages")
    
    def clear_message_history(self) -> None:
        """Clear message history."""
        self._message_history = []
        logger.info("Cleared message history")
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get current message history.
        
        Returns:
            List of messages in the model's native format
        """
        return self._message_history
    
    def _prepare_message_context(self, user_message: str) -> Union[str, List[Dict[str, Any]]]:
        """Prepare message context using history and user message.
        
        This method should be overridden by specific model implementations
        to format the context according to their API requirements.
        
        Args:
            user_message: The user's message
            
        Returns:
            Formatted context for the model
        """
        # Default implementation just returns the user message
        return user_message

class OpenAIFIPASupport(FIPAModelMixin):
    """Implementation of FIPA support for OpenAI models."""
    
    def _prepare_message_context(self, user_message: str) -> List[Dict[str, Any]]:
        """Prepare OpenAI-compatible message context.
        
        Args:
            user_message: The user's message
            
        Returns:
            List of messages in OpenAI format
        """
        # Add system message if not present
        if not self._message_history or self._message_history[0]["role"] != "system":
            messages = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            messages.extend(self._message_history)
        else:
            messages = list(self._message_history)  # Make a copy
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

class AnthropicFIPASupport(FIPAModelMixin):
    """Implementation of FIPA support for Anthropic models."""
    
    def _prepare_message_context(self, user_message: str) -> List[Dict[str, Any]]:
        """Prepare Anthropic-compatible message context.
        
        Args:
            user_message: The user's message
            
        Returns:
            List of messages in Anthropic format
        """
        # Use the message history directly
        messages = list(self._message_history)  # Make a copy
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

class OllamaFIPASupport(FIPAModelMixin):
    """Implementation of FIPA support for Ollama models."""
    
    def _prepare_message_context(self, user_message: str) -> List[Dict[str, Any]]:
        """Prepare Ollama-compatible message context.
        
        Args:
            user_message: The user's message
            
        Returns:
            List of messages in Ollama format
        """
        # Ollama expects a simple list of messages with role and content
        messages = list(self._message_history)  # Make a copy
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages