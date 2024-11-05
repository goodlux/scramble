from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import logging
from rich.table import Table

logger = logging.getLogger(__name__)

@dataclass
class CompressionStats:
    original_tokens: int
    compressed_tokens: int
    semantic_similarity: float
    timestamp: datetime
    context_id: str

    @property
    def compression_ratio(self) -> float:
        return self.original_tokens / max(1, self.compressed_tokens)

    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.compressed_tokens

class StatsTracker:
    def __init__(self):
        self.compression_history: List[CompressionStats] = []
        self.token_usage_history: List[Dict] = []

    def record_compression(self,
                         original_tokens: int,
                         compressed_tokens: int,
                         similarity_score: float,
                         context_id: str) -> None:
        """Record a new compression operation"""
        stats = CompressionStats(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            semantic_similarity=similarity_score,
            timestamp=datetime.utcnow(),
            context_id=context_id
        )
        self.compression_history.append(stats)
        logger.debug(f"Recorded compression: {stats.compression_ratio:.2f}x ratio")

    def record_token_usage(self,
                          input_tokens: int,
                          output_tokens: int,
                          context_tokens: int) -> None:
        """Record token usage for a conversation turn"""
        self.token_usage_history.append({
            'timestamp': datetime.utcnow(),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'context_tokens': context_tokens,
            'total_tokens': input_tokens + output_tokens + context_tokens
        })

    def get_compression_summary(self, hours: Optional[int] = None) -> Dict:
        """Get summary statistics for compression operations"""
        if not self.compression_history:
            return {}

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            history = [s for s in self.compression_history if s.timestamp > cutoff]
        else:
            history = self.compression_history

        if not history:
            return {}

        ratios = [s.compression_ratio for s in history]
        similarities = [s.semantic_similarity for s in history]
        tokens_saved = sum(s.tokens_saved for s in history)

        return {
            "compression_stats": {
                "avg_ratio": float(np.mean(ratios)),
                "max_ratio": float(np.max(ratios)),
                "min_ratio": float(np.min(ratios)),
                "total_compressions": len(history),
                "tokens_saved": tokens_saved,
            },
            "similarity_stats": {
                "avg_similarity": float(np.mean(similarities)),
                "min_similarity": float(np.min(similarities)),
            },
            "time_range": {
                "start": min(s.timestamp for s in history),
                "end": max(s.timestamp for s in history),
            }
        }

    def get_token_usage_summary(self, hours: Optional[int] = None) -> Dict:
        """Get summary statistics for token usage"""
        if not self.token_usage_history:
            return {}

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            history = [u for u in self.token_usage_history
                      if u['timestamp'] > cutoff]
        else:
            history = self.token_usage_history

        if not history:
            return {}

        return {
            "total_tokens": sum(u['total_tokens'] for u in history),
            "input_tokens": sum(u['input_tokens'] for u in history),
            "output_tokens": sum(u['output_tokens'] for u in history),
            "context_tokens": sum(u['context_tokens'] for u in history),
            "conversations": len(history),
            "avg_tokens_per_turn": float(np.mean([u['total_tokens'] for u in history]))
        }

    def generate_stats_table(self, hours: Optional[int] = None) -> Table:
        """Generate a rich table with stats for CLI display"""
        table = Table(title=f"Compression Stats {'(Last '+str(hours)+'h)' if hours else ''}")

        # Add compression stats
        comp_stats = self.get_compression_summary(hours)
        if comp_stats:
            table.add_row(
                "Compression Performance",
                f"Avg: {comp_stats['compression_stats']['avg_ratio']:.2f}x\n" +
                f"Max: {comp_stats['compression_stats']['max_ratio']:.2f}x\n" +
                f"Tokens Saved: {comp_stats['compression_stats']['tokens_saved']:,}"
            )

        # Add token usage stats
        token_stats = self.get_token_usage_summary(hours)
        if token_stats:
            table.add_row(
                "Token Usage",
                f"Total: {token_stats['total_tokens']:,}\n" +
                f"Input: {token_stats['input_tokens']:,}\n" +
                f"Output: {token_stats['output_tokens']:,}\n" +
                f"Context: {token_stats['context_tokens']:,}"
            )

        return table

# Global stats tracker instance
global_stats = StatsTracker()
