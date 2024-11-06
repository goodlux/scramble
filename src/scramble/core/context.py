from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
import numpy as np
import dateparser

@dataclass
class Context:
    """Represents a compressed conversation context."""
    id: str
    embeddings: np.ndarray
    compressed_tokens: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __eq__(self, other):
        if not isinstance(other, Context):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @property
    def size(self) -> int:
        """Return the size of the compressed context in tokens."""
        return len(self.compressed_tokens)

    @property
    def token_count(self) -> int:
        """Get actual token count from metadata or estimate from compressed tokens."""
        if 'token_count' in self.metadata:
            return self.metadata['token_count']
        return sum(chunk.get('size', 0) for chunk in self.compressed_tokens)

    @property
    def parent_id(self) -> Optional[str]:
        """Get parent context ID if it exists."""
        return self.metadata.get('parent_context')

    def summary(self) -> str:
        """Generate a brief summary of this context."""
        time_str = self.created_at.strftime("%Y-%m-%d %H:%M")
        topics_str = ", ".join(self.metadata.get('topics', []))
        chain_str = f"Part of thread: {self.parent_id[:8]}" if self.parent_id else "Start of thread"

        return f"[{time_str}] {topics_str} ({self.token_count} tokens) - {chain_str}"
