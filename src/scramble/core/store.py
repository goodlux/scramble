from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import pickle
import logging
import dateparser
from datetime import datetime, timedelta
import json
import numpy as np
from dateparser.conf import Settings
from .compressor import SemanticCompressor

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

        # Try to load metadata, reindex if missing or corrupted
        try:
            self.metadata = self._load_metadata()
            self._load_contexts()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info("Metadata missing or corrupted - rebuilding index...")
            contexts_found = self.reindex()
            logger.info(f"Reindexed {contexts_found} contexts")

    def get(self, context_id: str) -> Optional[Context]:
        """Retrieve a context by ID."""
        return self.contexts.get(context_id)

    def _create_full_file(self, context: Context) -> None:
        """Create a .full file for the context."""
        full_path = self.storage_path / 'full' / f"{context.id}.full"

        # Build metadata
        metadata = {
            'timestamp': context.created_at.isoformat(),
            'context_id': context.id,
            'compression_ratio': context.metadata.get('compression_ratio', 1.0),
            'parent_context': context.metadata.get('parent_context'),
            'chain_id': context.metadata.get('chain_id'),
            'usage': context.metadata.get('usage')
        }

        # Extract text content
        text_parts = []
        for token in context.compressed_tokens:
            if isinstance(token, dict) and 'content' in token:
                content = token['content']
                speaker = token.get('speaker', '')
                if speaker:
                    text_parts.append(f"{speaker}: {content}")
                else:
                    text_parts.append(content)
            elif isinstance(token, str):
                text_parts.append(token)

        text_content = "\n".join(text_parts)

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

    def get_date_range_str(self) -> str:
        """Get human readable date range of contexts."""
        try:
            dates = [
                datetime.fromisoformat(ctx.metadata['timestamp'])
                for ctx in self.contexts.values()
                if 'timestamp' in ctx.metadata
            ]

            if not dates:
                return "No dated contexts"

            oldest = min(dates)
            newest = max(dates)

            return f"{oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
        except Exception as e:
            logger.error(f"Error calculating date range: {e}")
            return "Date range unavailable"

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

        # Save context, full file, and metadata
        try:
            # Save binary context
            context_path = self.storage_path / f"{context.id}.ctx"
            with open(context_path, 'wb') as f:
                pickle.dump(context, f)

            # Create human-readable version
            self._create_full_file(context)

            # Save metadata
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

    def reindex(self):
        """Rebuild index from existing context files."""
        contexts = {}
        chains = []

        # Load all context files
        for ctx_file in self.storage_path.glob('*.ctx'):
            try:
                with open(ctx_file, 'rb') as f:
                    context = pickle.load(f)
                    contexts[context.id] = context

                    # Reconstruct chains from parent_context metadata
                    if 'parent_context' in context.metadata:
                        chains.append([
                            context.metadata['parent_context'],
                            context.id
                        ])
            except Exception as e:
                logger.error(f"Error loading {ctx_file}: {e}")

        # Rebuild metadata
        self.metadata = {
            'contexts': contexts,
            'chains': chains,
            'last_reindex': datetime.utcnow().isoformat()
        }

        return len(contexts)

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


class ContextManager:
    def __init__(self, store_path: Optional[str] = None):
            self.store = ContextStore(store_path)
            self.max_tokens = 4000  # Configurable token budget
            # Add the compressor
            self.compressor = SemanticCompressor()  # Make sure to import SemanticCompressor

    def process_message(self, message: str) -> List[Context]:
        """Process message and select relevant contexts."""
        candidates = []

        # Check for temporal references
        if dateparser.parse(message):
            historical = self.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        # Get recent contexts
        recent = self.store.get_recent_contexts(hours=48)
        candidates.extend(recent)

        # If we have current context, follow its chain
        current_id = self.store.metadata.get('current_context_id')
        if current_id:
            chain = self.get_conversation_chain(current_id)
            candidates.extend(chain)

        # Select within token budget
        return self.select_contexts(message, candidates)

    def find_contexts_by_timeframe(self, query: str) -> List[Context]:
        """Find contexts using natural language time reference."""
        try:
            # Use a simple dictionary with basic settings
            timeframe = dateparser.parse(
                query,
                settings={
                    'RELATIVE_BASE': datetime.now(),
                    'PREFER_DATES_FROM': 'past',
                    'TO_TIMEZONE': 'UTC'
                }
            )

            if not timeframe:
                return []

            # Add a window around the timeframe (e.g., ±12 hours)
            window_start = timeframe - timedelta(hours=12)
            window_end = timeframe + timedelta(hours=12)

            # Find contexts within the window
            matches = []
            for ctx in self.store.list():
                try:
                    if window_start <= ctx.created_at <= window_end:
                        matches.append(ctx)
                except (TypeError, AttributeError) as e:
                    logger.warning(f"Error comparing context dates: {e}")
                    continue

            return matches

        except Exception as e:
            logger.error(f"Error finding contexts by timeframe: {e}")
            return []

    def get_conversation_chain(self, context_id: str) -> List[Context]:
        """Get full chain of contexts connected to this one."""
        chain = []
        current_id = context_id

        # Follow parent links to build chain
        while current_id:
            context = self.store.get(current_id)
            if not context:
                break

            chain.append(context)
            current_id = context.parent_id

        return chain

    def select_contexts(self, message: str, candidates: List[Context]) -> List[Context]:
        """Select contexts within token budget with improved scoring."""
        scored = []
        now = datetime.now()

        # First, get message embedding once
        message_embedding = self.compressor.model.encode(message, convert_to_numpy=True)

        for ctx in candidates:
            score = 0.0

            # Recency score (exponential decay over 7 days)
            age = (now - ctx.created_at).total_seconds()
            recency_score = np.exp(-age / (7 * 24 * 3600))
            score += 0.3 * recency_score

            # Chain relationship score (boost for related contexts)
            if ctx.parent_id:
                chain_contexts = self.store.get_conversation_chain(ctx.id)
                chain_length = len(chain_contexts)
                score += 0.2 * min(chain_length / 5, 1.0)  # Cap at 5 contexts

            # Semantic relevance score using existing embeddings
            try:
                # Use the pre-computed embeddings from the context
                similarities = np.dot(ctx.embeddings, message_embedding)
                similarity_score = float(np.mean(similarities))
                score += 0.5 * similarity_score
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not compute similarity: {e}")

            scored.append((ctx, score, ctx.token_count))

        # Sort by score and select within budget
        scored.sort(key=lambda x: x[1], reverse=True)

        selected = []
        total_tokens = 0

        for ctx, score, tokens in scored:
            if total_tokens + tokens <= self.max_tokens:
                selected.append(ctx)
                total_tokens += tokens

                # Always include direct parent contexts
                if ctx.parent_id and total_tokens + tokens <= self.max_tokens:
                    parent = self.store.get(ctx.parent_id)
                    if parent and parent not in selected:
                        selected.append(parent)
                        total_tokens += parent.token_count

        return selected
