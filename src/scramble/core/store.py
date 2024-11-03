from typing import Dict, List, Optional
from pathlib import Path
import pickle
import logging
from .context import Context

logger = logging.getLogger(__name__)

class ContextStore:
    """Manages storage and retrieval of compressed contexts."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the context store."""
        self.storage_path = Path(storage_path or Path.home() / '.ramble' / 'store')
        self.contexts: Dict[str, Context] = {}
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_contexts()
    
    def _load_contexts(self) -> None:
        """Load all contexts from storage directory."""
        logger.debug(f"Loading contexts from {self.storage_path}")
        try:
            for context_file in self.storage_path.glob('*.pkl'):
                try:
                    with open(context_file, 'rb') as f:
                        context = pickle.load(f)
                        self.contexts[context.id] = context
                        logger.debug(f"Loaded context {context.id[:8]}")
                except Exception as e:
                    logger.error(f"Error loading context from {context_file}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.contexts)} contexts")
        except Exception as e:
            logger.error(f"Error accessing context store: {e}")
            raise
    
    def add(self, context: Context) -> None:
        """Store a compressed context."""
        logger.debug(f"Adding context {context.id[:8]}")
        self.contexts[context.id] = context
        
        try:
            context_path = self.storage_path / f"{context.id}.pkl"
            with open(context_path, 'wb') as f:
                pickle.dump(context, f)
            logger.debug(f"Saved context to {context_path}")
        except Exception as e:
            logger.error(f"Error saving context {context.id[:8]}: {e}")
            raise
    
    def get(self, context_id: str) -> Optional[Context]:
        """Retrieve a context by ID."""
        return self.contexts.get(context_id)
    
    def list(self) -> List[Context]:
        """List all stored contexts."""
        return list(self.contexts.values())
    
    def merge(self, context_ids: List[str]) -> Optional[Context]:
        """Merge multiple contexts into a new one."""
        contexts: List[Context] = []
        
        # Collect all valid contexts first
        for cid in context_ids:
            context = self.contexts.get(cid)
            if context is not None:
                contexts.append(context)
        
        # Check if we have enough contexts to merge
        if len(contexts) < 2:
            logger.warning("Cannot merge: insufficient valid contexts")
            return None
            
        # Merge contexts sequentially
        result = contexts[0]
        for other in contexts[1:]:
            result = result.merge(other)
        
        logger.debug(f"Merged {len(contexts)} contexts into new context {result.id[:8]}")
        self.add(result)
        return result
    
    def clear(self) -> None:
        """Clear all contexts from storage."""
        logger.warning("Clearing all contexts from store")
        for context_file in self.storage_path.glob('*.pkl'):
            context_file.unlink()
        self.contexts.clear()