from dataclasses import dataclass
from typing import Dict, List
import numpy as np

@dataclass
class CompressionStats:
    """Statistics about semantic compression performance"""
    original_tokens: int
    compressed_tokens: int
    unique_speakers: List[str]
    turns: int
    semantic_similarity: float  # similarity between original and compressed
    
    @property
    def compression_ratio(self) -> float:
        """Return compression ratio (original:compressed)"""
        return self.original_tokens / max(1, self.compressed_tokens)
    
    def to_dict(self) -> Dict:
        """Convert stats to dictionary for display"""
        return {
            'Original Tokens': self.original_tokens,
            'Compressed Tokens': self.compressed_tokens,
            'Compression Ratio': f'{self.compression_ratio:.2f}:1',
            'Unique Speakers': len(self.unique_speakers),
            'Conversation Turns': self.turns,
            'Semantic Retention': f'{self.semantic_similarity:.1%}'
        }