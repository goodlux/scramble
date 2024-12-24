from typing import Dict, Any, AsyncGenerator, Union, Optional
from .llm_model_base import LLMModelBase

class OtherLLMModel(LLMModelBase):
    """Implementation for other LLM providers."""
    
    def __init__(self):
        """Basic initialization."""
        super().__init__()
        self.temperature: float = 0.7
        
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
            
            if stream:
                return self._generate_stream(prompt, **params)
            else:
                return await self._generate_completion(prompt, **params)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            if stream:
                # Return an empty async generator for stream mode
                async def empty_generator() -> AsyncGenerator[str, None]:
                    if False:  # This will never yield
                        yield ""
                return empty_generator()
            else:
                # Return empty string for non-stream mode
                return ""
            

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