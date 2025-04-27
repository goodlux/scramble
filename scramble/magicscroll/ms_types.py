"""Shared types for MagicScroll."""
from typing import Dict, List, Any
from dataclasses import dataclass
from .ms_entry import MSEntry

@dataclass
class SearchResult:
    """Container for search results with source and confidence information."""
    entry: MSEntry
    score: float
    source: str  # 'graph', 'temporal', 'vector', 'hybrid'
    related_entries: List[MSEntry]
    context: Dict[str, Any]