from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, ClassVar

class ModelBase(ABC):
    """Base abstract class for all models (LLM or otherwise)"""
    
    model_type: ClassVar[str] = "base"
    
    @classmethod
    @abstractmethod
    async def create(cls, model_name: str) -> "ModelBase":
        """Create and initialize a new model instance."""
        pass
    
    @abstractmethod
    async def process_input(self, input_data: Any) -> Any:
        """Process any kind of input with the model."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass