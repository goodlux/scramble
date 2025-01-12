"""
Configuration management for Scramble.
A spiritual successor to the original config system.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import logging
import aiofiles
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API configuration including model settings."""
    api_key: str
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.7
    supports_vision: bool = True
    supports_tools: bool = True

@dataclass
class StorageConfig:
    """Storage configuration for MagicScroll."""
    redis_url: str = "redis://localhost:6379"
    chroma_path: str = "data/chroma"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    cache_dir: str = "data/cache"

@dataclass
class InterfaceConfig:
    """Interface configuration for both Ramble and RambleMAXX."""
    theme: str = "dark"
    max_history: int = 100
    show_debug: bool = False
    widget_layout: Optional[Dict[str, Any]] = None

class Config:
    """Central configuration management for Scramble."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.project_root = Path(__file__).parent
        self.model_config_dir = self.project_root / "model_config"
        self.config_path = self.project_root / "config.yaml"
        
        # Default configurations
        self.api: APIConfig = APIConfig(
            api_key="",
            model_id="claude-3-sonnet-20240229"
        )
        self.storage: StorageConfig = StorageConfig()
        self.interface: InterfaceConfig = InterfaceConfig()
        
    async def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file with async support."""
        if file_path.exists():
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return yaml.safe_load(content) or {}
        return {}

    async def _save_yaml(self, data: Dict[str, Any], file_path: Path) -> None:
        """Save data to YAML file."""
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(yaml.dump(data, indent=2))

    async def initialize(self) -> None:
        """Load and initialize all configurations."""
        try:
            # Load main config
            config = await self._load_yaml(self.config_path)
            
            # API configuration
            if 'api' in config:
                self.api = APIConfig(**config['api'])
            
            # Storage configuration
            if 'storage' in config:
                self.storage = StorageConfig(**config['storage'])
            
            # Interface configuration    
            if 'interface' in config:
                self.interface = InterfaceConfig(**config['interface'])
                
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Keep default values
            pass

    async def save(self) -> None:
        """Save current configuration."""
        config = {
            'api': {
                'api_key': self.api.api_key,
                'model_id': self.api.model_id,
                'max_tokens': self.api.max_tokens,
                'temperature': self.api.temperature,
                'supports_vision': self.api.supports_vision,
                'supports_tools': self.api.supports_tools
            },
            'storage': {
                'redis_url': self.storage.redis_url,
                'chroma_path': self.storage.chroma_path,
                'embedding_model': self.storage.embedding_model,
                'cache_dir': self.storage.cache_dir
            },
            'interface': {
                'theme': self.interface.theme,
                'max_history': self.interface.max_history,
                'show_debug': self.interface.show_debug,
                'widget_layout': self.interface.widget_layout
            },
            'last_updated': datetime.utcnow().isoformat()
        }
        
        await self._save_yaml(config, self.config_path)
        logger.info("Configuration saved successfully")

    async def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model."""
        models = await self._load_yaml(self.model_config_dir / "models.yaml")
        providers = await self._load_yaml(self.model_config_dir / "providers.yaml")
        
        model = models.get(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not found")
            
        provider = providers.get(model["provider"])
        if not provider:
            raise ValueError(f"Provider {model['provider']} not configured")
            
        return {
            "model_id": model["model_id"],
            "api_key": provider.get("api_key", self.api.api_key),
            "max_tokens": model.get("max_tokens", self.api.max_tokens),
            "temperature": model.get("temperature", self.api.temperature)
        }

    async def list_models(self) -> Dict[str, bool]:
        """List all available models with their status."""
        models = await self._load_yaml(self.model_config_dir / "models.yaml")
        providers = await self._load_yaml(self.model_config_dir / "providers.yaml")
        
        availability = {}
        for name, model in models.items():
            provider = providers.get(model["provider"])
            has_api_key = bool(
                provider and provider.get("api_key") or 
                self.api.api_key
            )
            availability[name] = has_api_key
        return availability

# Global instance
config = Config()