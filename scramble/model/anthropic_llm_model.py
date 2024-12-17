"""Anthropic Claude model implementation."""
from typing import Dict, Any, Optional
import logging
from .llm_model_base import LLMModelBase

logger = logging.getLogger(__name__)

class AnthropicLLMModel(LLMModelBase):
    """Implementation for Anthropic Claude models."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Anthropic model.
        
        Args:
            config: Optional configuration overrides
        """
        super().__init__()
        self.config = config or {}
        self.model_name = self.config.get("model", "claude-3-sonnet")
        
    def initialize(self) -> None:
        """Initialize model-specific settings."""
        # Verify we have the configuration we need
        required_config = ["api_key"]
        missing = [key for key in required_config if key not in self.config]
        if missing:
            raise ValueError(f"Missing required configuration keys: {missing}")
    
    def validate_config(self) -> bool:
        """Validate the model configuration."""
        try:
            # Check model name format
            valid_prefixes = ["claude-3-", "claude-2"]
            if not any(self.model_name.startswith(prefix) for prefix in valid_prefixes):
                logger.error(f"Invalid model name format: {self.model_name}")
                return False
            
            # Validate basic parameters
            params = self.config.get("parameters", {})
            if "temperature" in params and not 0 <= params["temperature"] <= 1:
                logger.error("Temperature must be between 0 and 1")
                return False
                
            if "top_p" in params and not 0 <= params["top_p"] <= 1:
                logger.error("Top_p must be between 0 and 1")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {str(e)}")
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using the Claude model.
        
        Args:
            prompt: The user's input prompt
            system_message: Optional system message for context
            **kwargs: Additional parameters to pass to the model
        
        Returns:
            The model's response text
        
        Raises:
            Exception: If there's an error generating the response
        """
        try:
            # Build messages list
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Merge parameters with priority:
            # 1. Explicitly passed kwargs
            # 2. Model config parameters
            # 3. Default parameters
            params = {
                "temperature": 0.7,
                "max_tokens": 4096,
                "top_p": 0.9,
                **self.config.get("parameters", {}),
                **kwargs
            }
            
            # Use the harness to make the API call
            response = await self.harness.complete(
                model=self.model_name,
                prompt=messages,
                **params
            )
            
            # Extract and return the response text
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "name": self.model_name,
            "provider": "Anthropic",
            "capabilities": [
                "chat",
                "code",
                "analysis",
                "creative",
                "math",
                "reasoning"
            ],
            "max_tokens": 4096 if "opus" in self.model_name or "sonnet" in self.model_name else 1024,
            "supports_system_message": True,
            "supports_functions": True,
            "supports_vision": "opus" in self.model_name or "sonnet" in self.model_name
        }
    
    def validate_response(self, response: str) -> bool:
        """Validate the model's response.
        
        Args:
            response: The response text to validate
        
        Returns:
            True if the response is valid, False otherwise
        """
        if not response or not isinstance(response, str):
            return False
            
        # Check for common error indicators
        error_indicators = [
            "I apologize, but I cannot",
            "I'm unable to",
            "ERROR:",
            "Exception:"
        ]
        
        return not any(indicator in response for indicator in error_indicators)