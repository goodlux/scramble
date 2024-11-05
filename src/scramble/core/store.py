from typing import Dict, List, Optional, Any
from pathlib import Path
import pickle
import logging
from datetime import datetime, timedelta
import json
import numpy as np

from .context import Context

logger = logging.getLogger(__name__)

class ContextStore:
    """Manages storage and retrieval of compressed contexts."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the context store."""
        self.storage_path = Path(storage_path or Path.home() / '.ramble' / 'store')
        self.contexts: Dict[str, Context] = {}
        self.metadata_file = self.storage_path / 'metadata.json'
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Store-level metadata
        self.metadata = self._load_metadata()
        self._load_contexts()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load or create store metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                return self._create_metadata()
        return self._create_metadata()

    def _create_metadata(self) -> Dict[str, Any]:
        """Create fresh store metadata."""
        metadata = {
            'created_at': datetime.utcnow().isoformat(),
            'last_interaction': datetime.utcnow().isoformat(),
            'conversation_count': 0,
            'context_groups': {},  # Group related contexts
            'context_chains': []   # Track conversation chains
        }
        self._save_metadata(metadata)
        return metadata

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save store metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f)

    def _load_contexts(self) -> None:
        """Load all contexts from storage directory."""
        logger.debug(f"Loading contexts from {self.storage_path}")
        try:
            for context_file in self.storage_path.glob('*.ctx'):
                try:
                    with open(context_file, 'rb') as f:
                        context = pickle.load(f)
                        logger.debug(f"Loaded context {context.id[:8]} from {context.created_at}")
                        self.contexts[context.id] = context
                except Exception as e:
                    logger.error(f"Error loading context from {context_file}: {e}")
                    continue

            logger.info(f"Loaded {len(self.contexts)} contexts")
        except Exception as e:
            logger.error("Error loading contexts: {e}")
            raise

    def add(self, context: Context) -> None:
        """Store a compressed context."""
        logger.debug(f"Adding context {context.id[:8]}")
        self.contexts[context.id] = context

        # Update store metadata
        self.metadata['last_interaction'] = datetime.utcnow().isoformat()
        self.metadata['conversation_count'] += 1

        # Track conversation chains
        if 'parent_context' in context.metadata:
            parent_id = context.metadata['parent_context']
            for chain in self.metadata['context_chains']:
                if parent_id in chain:
                    chain.append(context.id)
                    break
            else:
                self.metadata['context_chains'].append([parent_id, context.id])
        else:
            self.metadata['context_chains'].append([context.id])

        # Save context and metadata
        try:
            context_path = self.storage_path / f"{context.id}.ctx"
            with open(context_path, 'wb') as f:
                pickle.dump(context, f)
            self._save_metadata(self.metadata)
            logger.debug(f"Saved context to {context_path}")
        except Exception as e:
            logger.error(f"Error saving context {context.id[:8]}: {e}")
            raise

    def get_recent_contexts(self,
                          hours: int = 72,
                          limit: Optional[int] = None) -> List[Context]:
        """Get contexts from recent conversations."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [
            ctx for ctx in self.contexts.values()
            if ctx.created_at > cutoff
        ]
        recent.sort(key=lambda x: x.created_at, reverse=True)
        return recent[:limit] if limit else recent

    def get_conversation_chain(self, context_id: str) -> List[Context]:
        """Get ordered contexts in the same conversation chain."""
        for chain in self.metadata['context_chains']:
            if context_id in chain:
                return [
                    self.contexts[cid]
                    for cid in chain
                    if cid in self.contexts
                ]
        return []

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation history."""
        now = datetime.utcnow()
        return {
            'total_contexts': len(self.contexts),
            'total_conversations': self.metadata['conversation_count'],
            'last_interaction': datetime.fromisoformat(self.metadata['last_interaction']),
            'recent_contexts': len(self.get_recent_contexts(hours=24)),
            'conversation_chains': len(self.metadata['context_chains'])
        }

    def list(self) -> List[Context]:
        """List all stored contexts."""
        return list(self.contexts.values())

    def clear(self) -> None:
        """Clear all contexts from storage."""
        logger.warning("Clearing all contexts from store")
        for context_file in self.storage_path.glob('*.ctx'):
            context_file.unlink()
        self.contexts.clear()
        # Reset metadata but keep store creation time
        created_at = self.metadata['created_at']
        self.metadata = self._create_metadata()
        self.metadata['created_at'] = created_at
        self._save_metadata(self.metadata)
