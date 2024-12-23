"""
DEPRECATED: This interface is being replaced
Keeping for reference until new interface is fully implemented.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

@dataclass
class ScrollEntry:
    """A single entry in the scroll."""
    id: UUID
    content: str
    model: Optional[str]  # Which model (if AI response)
    timestamp: datetime
    metadata: Dict[str, Any]  # For context, tools, etc.
    parent_id: Optional[UUID] = None  # For threading/context

class Scroll:
    """
    The continuous timeline of all interactions.
    This is the core concept - everything else builds on this.
    """
    def __init__(self):
        self.entries: List[ScrollEntry] = []
        self.current_context: Optional[UUID] = None
    
    async def add_entry(
        self, 
        content: str, 
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScrollEntry:
        """Add a new entry to the scroll."""
        entry = ScrollEntry(
            id=uuid4(),
            content=content,
            model=model,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            parent_id=self.current_context
        )
        self.entries.append(entry)
        self.current_context = entry.id
        return entry
    
    def filter_view(
        self,
        models: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        context_id: Optional[UUID] = None
    ) -> List[ScrollEntry]:
        """Get filtered view of the scroll."""
        filtered = self.entries

        if models:
            filtered = [e for e in filtered if e.model in models]
        if since:
            filtered = [e for e in filtered if e.timestamp >= since]
        if until:
            filtered = [e for e in filtered if e.timestamp <= until]
        if context_id:
            filtered = self._get_context_thread(context_id)

        return filtered

    def _get_context_thread(self, context_id: UUID) -> List[ScrollEntry]:
        """Get the thread of entries related to a context."""
        thread = []
        current = context_id
        while current:
            entry = next((e for e in self.entries if e.id == current), None)
            if entry:
                thread.append(entry)
                current = entry.parent_id
            else:
                break
        return list(reversed(thread))