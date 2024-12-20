"""Configuration management for Scramble models."""
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages model configurations and API keys."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_dir = config_path or Path.home() / ".scramble" / "config"
        self.providers_file = self.config_dir / "providers.yaml"
        self.models_file = self.config_dir / "models.yaml"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self.providers = self._load_yaml(self.providers_file)
        self.models = self._load_yaml(self.models_file)
        
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file or return empty dict if not exists."""
        if file_path.exists():
            return yaml.safe_load(file_path.read_text()) or {}
        return {}

    def _save_yaml(self, data: Dict[str, Any], file_path: Path) -> None:
        """Save data to YAML file."""
        file_path.write_text(yaml.dump(data, indent=2))

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a model including its API key."""
        model = self.models.get(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not found")
            
        provider = self.providers.get(model["provider"])
        if not provider:
            raise ValueError(f"Provider {model['provider']} not configured")
            
        if not provider.get("api_key"):
            raise ValueError(f"API key not set for {model['provider']}")
            
        return {
            "model": model["model_id"],
            "api_key": provider["api_key"]
        }

    def set_provider_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not found")
            
        self.providers[provider]["api_key"] = api_key
        self._save_yaml(self.providers, self.providers_file)

    def list_models(self) -> Dict[str, bool]:
        """List all models and whether they're configured."""
        configured = {}
        for name, model in self.models.items():
            provider = self.providers.get(model["provider"])
            configured[name] = bool(provider and provider.get("api_key"))
        return configured