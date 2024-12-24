"""Configuration management for Scramble models."""
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import logging
import aiofiles  # For async file operations

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages model configurations and API keys."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config_dir = Path(__file__).parent  # Using model_config directory
        self.providers_file = self.config_dir / "providers.yaml"
        self.models_file = self.config_dir / "models.yaml"
        
    async def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file or return empty dict if not exists."""
        if file_path.exists():
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return yaml.safe_load(content) or {}
        return {}

    async def _save_yaml(self, data: Dict[str, Any], file_path: Path) -> None:
        """Save data to YAML file."""
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(yaml.dump(data, indent=2))

    async def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a model including its API key.
        
        Args:
            model_name: Friendly name/key for the model (e.g., 'sonnet')
            
        Returns:
            Dict containing model configuration including:
            - model_id: The actual model identifier
            - api_key: The provider's API key
            - Any additional model-specific parameters
        """
        models = await self._load_yaml(self.models_file)
        providers = await self._load_yaml(self.providers_file)
        
        model = models.get(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not found")
            
        provider = providers.get(model["provider"])
        if not provider:
            raise ValueError(f"Provider {model['provider']} not configured")
            
        if not provider.get("api_key"):
            raise ValueError(f"API key not set for {model['provider']}")
            
        return {
            "model_id": model["model_id"],  # Changed from "model" to "model_id"
            "api_key": provider["api_key"],
            **model.get("parameters", {})  # Include any additional parameters
        }


    async def set_provider_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider."""
        providers = await self._load_yaml(self.providers_file)
        
        if provider not in providers:
            raise ValueError(f"Provider {provider} not found")
            
        providers[provider]["api_key"] = api_key
        await self._save_yaml(providers, self.providers_file)

    async def list_models(self) -> Dict[str, bool]:
        """List all models and whether they're configured."""
        models = await self._load_yaml(self.models_file)
        providers = await self._load_yaml(self.providers_file)
        
        configured = {}
        for name, model in models.items():
            provider = providers.get(model["provider"])
            configured[name] = bool(provider and provider.get("api_key"))
        return configured