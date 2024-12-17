"""Implementation using LiteLLM for model interaction."""
from typing import Optional, Dict, Any, Union, AsyncGenerator
import logging

from .llm_model_base import LLMModelBase

logger = logging.getLogger(__name__)

class OtherLLMModel(LLMModelBase):
    """Model implementation using LiteLLM."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.model_name = config.get("model", "claude-3-sonnet")
        
        # Initialize any model-specific parameters
        self.max_context_length = config.get("max_context_length", 4096)
        self.temperature = config.get("temperature", 0.7)
        
        logger.info(f"Initialized {self.model_name} with LiteLLM")
    
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
            "name": self.model_name,
            "provider": "LiteLLM",
            "max_context_length": self.max_context_length,
            "supports_streaming": True,
            "supports_tools": False  # Will add tool support later
        }