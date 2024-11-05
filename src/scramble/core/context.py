# src/scramble/core/context.py
from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime
import numpy as np

@dataclass
class Context:
    """Represents a compressed conversation context."""
    id: str
    embeddings: np.ndarray
    compressed_tokens: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def size(self) -> int:
        """Return the size of the compressed context in tokens."""
        return len(self.compressed_tokens)