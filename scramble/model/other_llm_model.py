"""Implementation using LiteLLM for model interaction."""
from typing import Optional, Dict, Any, Union, AsyncGenerator
import logging

from .llm_model_base import LLMModelBase

logger = logging.getLogger(__name__)

class OtherLLMModel(LLMModelBase):
    """Model implementation using LiteLLM."""
    
    def __init__(self, model_name: str):
        # Renamed from config param to model_name for consistency
        super().__init__(model_name)
        
        # Get parameters with defaults if not specified
        self.max_context_length = 4096  # Moved default here instead of from config
        self.temperature = 0.7
    
    async def generate_response(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using LiteLLM."""
        try:
            params = {
                "temperature": self.temperature,
                "max_tokens": kwargs.get("max_tokens", self.max_context_length),
                **kwargs
            }
            
            return await super().generate_response(
                prompt=prompt,
                stream=stream,
                **params
            )
            
        except Exception as e:
            logger.error(f"Error generating response with {self.model_name}: {e}")
            raise
            

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "model_id": self.model_id,  # Added model_id
            "provider": "LiteLLM",
            "max_context_length": self.max_context_length,
            "supports_streaming": True,
            "supports_tools": False
        }