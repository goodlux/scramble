from typing import Dict, List, Optional, Any, Union,Tuple
from pathlib import Path
import pickle
import logging
import dateparser
from datetime import datetime, timedelta
import json
import numpy as np
from .compressor import SemanticCompressor
from .context import Context

logger = logging.getLogger(__name__)

class ContextStore:
    """Manages basic storage and retrieval of contexts."""
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or Path.home() / '.ramble' / 'store')
        self.contexts: Dict[str, Context] = {}
        self.metadata_file = self.storage_path / 'metadata.json'
        self.storage_path.mkdir(parents=True, exist_ok=True)

        try:
            self.metadata = self._load_metadata()
            self._load_contexts()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info("Metadata missing or corrupted - rebuilding index...")
            contexts_found = self.reindex()
            logger.info(f"Reindexed {contexts_found} contexts")


    def validate_timestamps(self):
        """Validate and normalize timestamps in all contexts."""
        for ctx in self.contexts.values():
            try:
                timestamp = ctx.metadata.get('timestamp')
                if isinstance(timestamp, str):
                    ctx.metadata['timestamp'] = datetime.fromisoformat(timestamp)
                if not hasattr(ctx, 'created_at'):
                    ctx.created_at = ctx.metadata.get('timestamp') or datetime.utcnow()
            except (ValueError, AttributeError) as e:
                logger.error(f"Invalid timestamp in context {ctx.id}: {e}")

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
            'context_chains': [],
            'current_context_id': None
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
                        self.contexts[context.id] = context
                except Exception as e:
                    logger.error(f"Error loading context from {context_file}: {e}")
                    continue

            logger.info(f"Loaded {len(self.contexts)} contexts")
        except Exception as e:
            logger.error(f"Error accessing context store: {e}")
            raise

    def _get_chain(self, context_id: str) -> List[Context]:
        """Internal method to get chain contexts."""
        logger.debug(f"Getting chain for context {context_id[:8]}")
        chain = []
        visited = set()
        current_id = context_id

        while current_id and current_id not in visited:
            visited.add(current_id)
            context = self.contexts.get(current_id)

            if not context:
                logger.debug(f"Chain broken - context {current_id[:8]} not found")
                break

            chain.append(context)
            current_id = context.metadata.get('parent_context')
            if current_id:
                logger.debug(f"Following chain to parent {current_id[:8]}")

        logger.debug(f"Chain complete - found {len(chain)} contexts")
        return chain[::-1]

    def add(self, context: Context) -> None:
        """Store a compressed context."""
        logger.debug(f"Adding context {context.id[:8]}")
        self.contexts[context.id] = context
        self.metadata['current_context_id'] = context.id

        # Update metadata
        self.metadata['last_interaction'] = datetime.utcnow().isoformat()
        self.metadata['conversation_count'] += 1

        # Update chain relationships
        parent_id = context.metadata.get('parent_context')
        if parent_id:
            chain_found = False
            for chain in self.metadata['context_chains']:
                if parent_id in chain:
                    chain.append(context.id)
                    chain_found = True
                    break
            if not chain_found:
                self.metadata['context_chains'].append([parent_id, context.id])
        else:
            self.metadata['context_chains'].append([context.id])

        # Save to disk
        try:
            context_path = self.storage_path / f"{context.id}.ctx"
            with open(context_path, 'wb') as f:
                pickle.dump(context, f)
            self._save_metadata(self.metadata)
            logger.debug(f"Saved context to {context_path}")
        except Exception as e:
            logger.error(f"Error saving context {context.id[:8]}: {e}")
            raise

    def get_recent_contexts(self, hours: int = 48, limit: Optional[int] = None) -> List[Context]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = []

        for ctx in self.contexts.values():
            try:
                # Try multiple timestamp sources in order
                timestamp = None

                # Try metadata timestamp
                if 'timestamp' in ctx.metadata:
                    if isinstance(ctx.metadata['timestamp'], datetime):
                        timestamp = ctx.metadata['timestamp']
                    elif isinstance(ctx.metadata['timestamp'], str):
                        timestamp = datetime.fromisoformat(ctx.metadata['timestamp'])

                # Fall back to created_at
                if not timestamp and hasattr(ctx, 'created_at'):
                    timestamp = ctx.created_at

                # Last resort: current time
                if not timestamp:
                    timestamp = datetime.utcnow()
                    logger.warning(f"No valid timestamp found for context {ctx.id}")

                if timestamp > cutoff:
                    recent.append(ctx)

            except Exception as e:
                logger.error(f"Error processing context {ctx.id}: {e}")
                continue

        recent.sort(key=lambda x: x.metadata.get('timestamp', datetime.min), reverse=True)
        return recent[:limit] if limit else recent

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation history."""
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

    def reindex(self) -> int:
        """Rebuild context index and chain relationships."""
        logger.info("Starting reindex operation")
        contexts = {}
        parent_map = {}
        chains = []

        # Load contexts and build parent map
        for ctx_file in self.storage_path.glob('*.ctx'):
            try:
                with open(ctx_file, 'rb') as f:
                    context = pickle.load(f)
                    contexts[context.id] = context
                    parent_id = context.metadata.get('parent_context')
                    if parent_id:
                        if parent_id not in parent_map:
                            parent_map[parent_id] = []
                        parent_map[parent_id].append(context.id)
            except Exception as e:
                logger.error(f"Error loading {ctx_file}: {e}")

        # Rebuild chains
        processed = set()

        def build_chain(start_id: str) -> List[str]:
            if start_id in processed:
                return []
            chain = [start_id]
            processed.add(start_id)
            children = sorted(
                parent_map.get(start_id, []),
                key=lambda x: contexts[x].created_at
            )
            for child_id in children:
                chain.extend(build_chain(child_id))
            return chain

        # Build chains from roots
        for ctx_id in contexts:
            if ctx_id not in processed:
                parent_id = contexts[ctx_id].metadata.get('parent_context')
                if not parent_id or parent_id not in contexts:
                    chain = build_chain(ctx_id)
                    if chain:
                        chains.append(chain)

        # Update store state
        self.contexts = contexts
        self.metadata['context_chains'] = chains
        self.metadata['conversation_count'] = len(contexts)
        self._save_metadata(self.metadata)

        return len(contexts)

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """Get date range of all contexts."""
        dates = []
        for ctx in self.contexts.values():
            timestamp = ctx.metadata.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dates.append(datetime.fromisoformat(timestamp))
                    else:
                        dates.append(timestamp)
                except (ValueError, TypeError):
                    dates.append(ctx.created_at)
            else:
                dates.append(ctx.created_at)

        if not dates:
            now = datetime.utcnow()
            return (now, now)

        return (min(dates), max(dates))

    def get_date_range_str(self) -> str:
        """Get human readable date range string."""
        start, end = self.get_date_range()
        return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"

    def add_with_full(self, context: Context) -> None:
        """Store both compressed and full versions of a context."""
        logger.debug(f"Starting add_with_full for context {context.id[:8]}")

        # Log paths before saving
        full_dir = self.storage_path / 'full'
        logger.debug(f"Full directory path: {full_dir}")
        logger.debug(f"Full directory exists: {full_dir.exists()}")

        # Save compressed version normally
        self.add(context)
        logger.debug(f"Saved compressed version")

        # Create and verify full directory
        full_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created/verified full directory")

        # Create full version
        full_context = Context(
            id=context.id,
            embeddings=context.embeddings,
            compressed_tokens=[{
                'content': context.text_content,
                'speaker': None,
                'size': len(context.text_content)
            }],
            metadata={
                **context.metadata,
                'is_full_version': True,
                'original_id': context.id
            },
            created_at=context.created_at,
            updated_at=context.updated_at
        )

        try:
            context_path = full_dir / f"{context.id}.ctx"
            logger.debug(f"Attempting to save full context to {context_path}")
            with open(context_path, 'wb') as f:
                pickle.dump(full_context, f)
            logger.debug(f"Successfully saved full context")
        except Exception as e:
            logger.error(f"Error saving full context {context.id[:8]}: {e}")
            raise

        # Save full version
        full_path = self.storage_path / 'full'
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created full directory at {full_path}")

        try:
            context_path = full_path / f"{context.id}.ctx"
            with open(context_path, 'wb') as f:
                pickle.dump(full_context, f)
            logger.debug(f"Successfully saved full context to {context_path}")
        except Exception as e:
            logger.error(f"Error saving full context {context.id[:8]}: {e}")
            raise


class ContextManager:
    """Handles higher-level context operations and chain management."""
    def __init__(self, store_path: Optional[str] = None):
        self.store = ContextStore(store_path)
        self.max_tokens = 4000
        self.compressor = SemanticCompressor()

        # Add scoring configuration
        self.scoring_config = {
            'recency_weight': 0.05,
            'chain_bonus': 0.4,
            'decay_days': 14
        }

    def get_conversation_chain(self, context_id: str) -> List[Context]:
        """Public method to access conversation chains."""
        return self.store._get_chain(context_id)

    def find_contexts_by_timeframe(self, query: str) -> List[Context]:
        """Find contexts using natural language time reference."""
        try:
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

            window_start = timeframe - timedelta(hours=12)
            window_end = timeframe + timedelta(hours=12)

            matches = []
            for ctx in self.store.list():
                try:
                    if window_start <= ctx.created_at <= window_end:
                        matches.append(ctx)
                except Exception as e:
                    logger.warning(f"Error comparing context dates: {e}")
                    continue

            return matches

        except Exception as e:
            logger.error(f"Error finding contexts by timeframe: {e}")
            return []

    def select_contexts(self, message: str, candidates: List[Context]) -> List[Context]:
            """Select contexts within token budget with improved scoring."""
            if not candidates:
                return []

            scored = []
            now = datetime.now()

            try:
                message_embedding = self.compressor.model.encode(message, convert_to_numpy=True)
            except Exception as e:
                logger.error(f"Error computing message embedding: {e}")
                return []

            for ctx in candidates:
                try:
                    # Initialize score components
                    recency_score = 0.0
                    semantic_score = 0.0
                    chain_bonus = 0.0

                    # Recency score
                    age = (now - ctx.created_at).total_seconds()
                    recency_score = np.exp(-age / (self.scoring_config['decay_days'] * 24 * 3600))

                    # Chain bonus
                    if ctx.metadata.get('parent_context'):
                        chain_bonus = self.scoring_config['chain_bonus']

                    # Semantic similarity
                    if hasattr(ctx, 'embeddings') and ctx.embeddings is not None:
                        chunk_similarities = np.dot(ctx.embeddings, message_embedding)
                        top_chunk_scores = np.sort(chunk_similarities)[-3:]
                        semantic_score = float(np.mean(top_chunk_scores))

                        ctx.metadata['chunk_similarities'] = {
                            'top_scores': top_chunk_scores.tolist(),
                            'mean_score': semantic_score
                        }

                    # Calculate final score
                    final_score = (
                        (1 - self.scoring_config['recency_weight']) * semantic_score +
                        self.scoring_config['recency_weight'] * recency_score +
                        chain_bonus
                    )

                    # Store scoring details
                    ctx.metadata['scoring'] = {
                        'final_score': float(final_score),
                        'semantic_score': float(semantic_score),
                        'recency_score': float(recency_score),
                        'chain_bonus': float(chain_bonus),
                        'timestamp': now.isoformat(),
                        'query': message
                    }

                    scored.append((ctx, final_score, ctx.token_count))

                except Exception as e:
                    logger.error(f"Error scoring context {ctx.id}: {e}")
                    continue

            # Sort by score
            scored.sort(key=lambda x: x[1], reverse=True)

            selected = []
            total_tokens = 0

            for ctx, score, tokens in scored:
                if total_tokens + tokens <= self.max_tokens:
                    ctx.metadata['selection_reason'] = (
                        'semantic_match' if ctx.metadata.get('scoring', {}).get('semantic_score', 0) > 0.5
                        else 'chain_bonus' if ctx.metadata.get('scoring', {}).get('chain_bonus', 0) > 0
                        else 'time_window'
                    )
                    selected.append(ctx)
                    total_tokens += tokens

            return selected

    def process_message(self, message: str) -> List[Context]:
        """Process message and select relevant contexts."""
        candidates = []

        # Get all contexts
        all_contexts = self.store.list()

        # Check for temporal references
        if dateparser.parse(message):
            historical = self.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        # Get semantic matches from all contexts
        similar = self.compressor.find_similar(message, all_contexts, top_k=10)
        candidates.extend([ctx for ctx, _, _ in similar])

        # Add recent contexts
        recent = self.store.get_recent_contexts(hours=168)
        candidates.extend(recent)

        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for ctx in candidates:
            if ctx.id not in seen:
                seen.add(ctx.id)
                unique_candidates.append(ctx)

        return self.select_contexts(message, unique_candidates)
