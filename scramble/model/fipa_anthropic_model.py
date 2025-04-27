"""FIPA-enhanced Anthropic model implementation."""
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, cast
import logging
import json

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ModelParam, Message

from scramble.utils.logging import get_logger
from .anthropic_llm_model import AnthropicLLMModel
from .fipa_model_support import AnthropicFIPASupport

logger = get_logger(__name__)

class FIPAAnthropicModel(AnthropicFIPASupport, AnthropicLLMModel):
    """Anthropic Claude model with FIPA ACL support."""
    
    @classmethod
    async def create(cls, model_name: str) -> 'FIPAAnthropicModel':
        """Create a new FIPA-enhanced Anthropic model instance.
        
        Args:
            model_name: The name of the model to use
            
        Returns:
            Initialized model instance
        """
        model = cls()
        await model._init(model_name)
        return model
    
    async def _init(self, model_name: str) -> None:
        """Initialize the model."""
        self._anthropic = None
        self._model_name = model_name
        self._context_buffer = []
        self._anthropic = AsyncAnthropic()
        logger.info(f"Initialized FIPA-enhanced Anthropic model: {model_name}")
    
    async def generate_response(self, prompt: str) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using the model.
        
        This version uses FIPA message history if available.
        
        Args:
            prompt: The prompt to generate a response for
            
        Returns:
            The generated response as a string or stream
        """
        try:
            # Check if we have a message history
            if self._message_history:
                # Use FIPA-aware message preparation
                messages = self._prepare_message_context(prompt)
                
                logger.info(f"Generating response with {len(messages)} messages in history")
                
                # Create API request with messages
                response = await self._anthropic.messages.create(
                    model=self._model_name,
                    messages=cast(List[MessageParam], messages),
                    max_tokens=1024
                )
                
                # Add the response to message history
                self._message_history.append({
                    "role": "assistant", 
                    "content": response.content[0].text
                })
                
                return response.content[0].text
            else:
                # Fall back to standard method
                return await super().generate_response(prompt)
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"
    
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream a response from the model.
        
        Args:
            prompt: The prompt to generate a response for
            
        Yields:
            Response chunks as they are generated
        """
        try:
            # Check if we have a message history
            if self._message_history:
                # Use FIPA-aware message preparation
                messages = self._prepare_message_context(prompt)
                
                logger.info(f"Streaming response with {len(messages)} messages in history")
                
                # Create streaming API request with messages
                response_stream = await self._anthropic.messages.create(
                    model=self._model_name,
                    messages=cast(List[MessageParam], messages),
                    max_tokens=1024,
                    stream=True
                )
                
                full_response = ""
                
                # Stream the response
                async for chunk in response_stream:
                    if chunk.type == "content_block_delta" and chunk.delta.text:
                        full_response += chunk.delta.text
                        yield chunk.delta.text
                
                # Add the full response to message history
                self._message_history.append({
                    "role": "assistant", 
                    "content": full_response
                })
            else:
                # Fall back to standard method
                async for chunk in super().stream_response(prompt):
                    yield chunk
        
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield f"Error: {str(e)}"