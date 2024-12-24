from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, ClassVar

class ModelBase(ABC):
    """Base abstract class for all models"""
    
    @classmethod
    @abstractmethod
    async def create(cls, model_name: str) -> "ModelBase":
        """Create and initialize a new model instance."""
        pass