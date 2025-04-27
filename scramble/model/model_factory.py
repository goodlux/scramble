"""Model factory for creating the appropriate model type."""
from typing import Optional, Dict, Any, Type

from scramble.utils.logging import get_logger
from .llm_model_base import LLMModelBase
from .anthropic_llm_model import AnthropicLLMModel
from .ollama_llm_model import OllamaLLMModel
from .fipa_anthropic_model import FIPAAnthropicModel
from .fipa_ollama_model import FIPAOllamaModel

logger = get_logger(__name__)

class ModelFactory:
    """Factory for creating model instances."""
    
    @staticmethod
    async def create_model(
        model_name: str,
        model_type: Optional[str] = None,
        use_fipa: bool = True,
        model_config: Optional[Dict[str, Any]] = None
    ) -> LLMModelBase:
        """Create a model instance of the appropriate type.
        
        Args:
            model_name: Name of the model to create
            model_type: Optional type of model (anthropic, ollama, etc.)
                        If not provided, it will be inferred from model_name
            use_fipa: Whether to use FIPA-enhanced models
            model_config: Optional model configuration
            
        Returns:
            Initialized model instance
        """
        # Infer model type if not provided
        if not model_type:
            if "claude" in model_name.lower() or "anthropic" in model_name.lower():
                model_type = "anthropic"
            elif "gpt" in model_name.lower() or "openai" in model_name.lower():
                model_type = "openai"
            elif "llama" in model_name.lower() or "mistral" in model_name.lower():
                model_type = "ollama"
            else:
                logger.warning(f"Could not infer model type from name: {model_name}")
                model_type = "anthropic"  # Default to Anthropic
        
        # Create the appropriate model type
        if model_type == "anthropic":
            if use_fipa:
                logger.info(f"Creating FIPA-enhanced Anthropic model: {model_name}")
                return await FIPAAnthropicModel.create(model_name)
            else:
                logger.info(f"Creating standard Anthropic model: {model_name}")
                return await AnthropicLLMModel.create(model_name)
        
        elif model_type == "ollama":
            if use_fipa:
                logger.info(f"Creating FIPA-enhanced Ollama model: {model_name}")
                return await FIPAOllamaModel.create(model_name)
            else:
                logger.info(f"Creating standard Ollama model: {model_name}")
                return await OllamaLLMModel.create(model_name)
        
        # Add other model types as needed
        
        else:
            # Default to Anthropic models
            logger.warning(f"Unknown model type: {model_type}, defaulting to Anthropic")
            if use_fipa:
                return await FIPAAnthropicModel.create(model_name)
            else:
                return await AnthropicLLMModel.create(model_name)
    
    @staticmethod
    def get_model_class(
        model_type: str,
        use_fipa: bool = True
    ) -> Type[LLMModelBase]:
        """Get the model class for a given type.
        
        Args:
            model_type: Type of model (anthropic, ollama, etc.)
            use_fipa: Whether to use FIPA-enhanced models
            
        Returns:
            Model class
        """
        if model_type == "anthropic":
            return FIPAAnthropicModel if use_fipa else AnthropicLLMModel
        
        elif model_type == "ollama":
            return FIPAOllamaModel if use_fipa else OllamaLLMModel
        
        # Add other model types as needed
        
        else:
            # Default to Anthropic models
            logger.warning(f"Unknown model type: {model_type}, defaulting to Anthropic")
            return FIPAAnthropicModel if use_fipa else AnthropicLLMModel