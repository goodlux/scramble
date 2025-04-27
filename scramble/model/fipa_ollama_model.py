"""FIPA-enhanced Ollama model implementation."""
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, TypedDict
import logging
import json

from httpx import AsyncClient

from scramble.utils.logging import get_logger
from .ollama_llm_model import OllamaLLMModel, OllamaModelOptions
from .fipa_model_support import OllamaFIPASupport

logger = get_logger(__name__)

class FIPAOllamaModel(OllamaFIPASupport, OllamaLLMModel):
    """Ollama model with FIPA ACL support."""
    
    @classmethod
    async def create(cls, model_name: str) -> 'FIPAOllamaModel':
        """Create a new FIPA-enhanced Ollama model instance.
        
        Args:
            model_name: The name of the model to use
            
        Returns:
            Initialized model instance
        """
        model = cls()
        # Use the base class initialization
        await model._init(model_name)
        return model
    
    async def _init(self, model_name: str) -> None:
        """Initialize the model."""
        # Standard Ollama initialization
        self.model_name = model_name
        self.client = AsyncClient(timeout=300)  # 5 minute timeout
        self.api_base = "http://localhost:11434/api"
        logger.info(f"Initialized FIPA-enhanced Ollama model: {model_name}")
    
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
                
                # Get model options
                options = self._get_model_options({})
                
                # Create API request with messages
                response = await self.client.post(
                    f"{self.api_base}/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "options": options,
                        "stream": False
                    }
                )
                
                response.raise_for_status()
                response_data = response.json()
                
                content = response_data.get("message", {}).get("content", "")
                
                # Add the response to message history
                self._message_history.append({
                    "role": "assistant", 
                    "content": content
                })
                
                return content
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
                
                # Get model options
                options = self._get_model_options({})
                
                # Create streaming API request with messages
                response = await self.client.post(
                    f"{self.api_base}/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "options": options,
                        "stream": True
                    },
                    timeout=None
                )
                
                response.raise_for_status()
                
                full_response = ""
                
                # Stream the response
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                        
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            chunk_text = chunk["message"]["content"]
                            full_response += chunk_text
                            yield chunk_text
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from Ollama: {line}")
                
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