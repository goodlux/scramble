"""MagicScroll - The unified knowledge store."""
from .magic_scroll import MagicScroll
from .ms_entry import MSEntry, MSConversation, MSDocument, MSImage, MSCode, EntryType
from .ms_index import MSIndex
from .ms_store import MSStore
from .ms_search import MSSearch
from .ms_graph import MSGraphManager
from .ms_types import SearchResult

__all__ = [
    'MagicScroll',
    'MSEntry',
    'MSConversation',
    'MSDocument',
    'MSImage',
    'MSCode',
    'EntryType',
    'MSIndex',
    'MSSearch',
    'MSStore',
    'MSGraphManager',
    'SearchResult'
]