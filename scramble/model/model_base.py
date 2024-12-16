from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ModelBase(ABC):
    """Base abstract class for all models"""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the model"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate model configuration"""
        pass