from typing import Dict, List, Any, Optional
import uuid
import numpy as np
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
from .context import Context

logger = logging.getLogger(__name__)

class SemanticCompressor:
    """Core compression engine for semantic compression of text."""

    def __init__(self,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 512):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into manageable chunks."""
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        current_speaker = None

        for line in lines:
            # Detect speaker changes
            if line.startswith('Human: '):
                current_speaker = 'Human'
                line = line[7:]  # Remove speaker prefix
            elif line.startswith('Assistant: '):
                current_speaker = 'Assistant'
                line = line[11:]  # Remove speaker prefix

            line = line.strip()
            if not line:
                continue

            if current_size + len(line) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        'content': ' '.join(current_chunk),
                        'speaker': current_speaker,
                        'size': current_size
                    })
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line)

        if current_chunk:
            chunks.append({
                'content': ' '.join(current_chunk),
                'speaker': current_speaker,
                'size': current_size
            })

        return chunks

    def compress(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Context:
        """Compress text with enhanced metadata."""
        chunks = self._chunk_text(text)

        # Extract just the content strings from chunks for encoding
        chunk_texts = [chunk['content'] for chunk in chunks]

        # Generate embeddings
        embeddings = self.model.encode(chunk_texts, convert_to_numpy=True)

        compression_metadata = {
            'original_length': len(text),
            'compressed_length': sum(len(c['content']) for c in chunks),
            'timestamp': datetime.utcnow().isoformat(),
            'compression_ratio': len(text) / sum(len(c['content']) for c in chunks),
            **(metadata or {})
        }

        # Create context with metadata
        return Context(
            id=str(uuid.uuid4()),
            embeddings=embeddings,
            compressed_tokens=chunks,
            metadata=compression_metadata
        )

    def find_similar(self,
                    query: str,
                    contexts: List[Context],
                    top_k: int = 3,
                    recency_weight: float = 0.2) -> List[tuple[Context, float, Dict[str, Any]]]:
        """Find contexts using enhanced similarity scoring."""
        if not contexts:
            return []

        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        now = datetime.utcnow()

        results = []
        for context in contexts:
            # Calculate chunk similarities
            chunk_similarities = np.dot(context.embeddings, query_embedding)

            # Get top 3 matching chunks instead of just best
            top_chunk_indices = np.argsort(chunk_similarities)[-3:]
            top_chunk_scores = chunk_similarities[top_chunk_indices]

            # Calculate aggregate context score
            semantic_score = np.mean(top_chunk_scores)

            # Calculate recency score (0-1)
            try:
                timestamp = context.metadata.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                elif timestamp is None:
                    timestamp = now

                age = (now - timestamp).total_seconds()
                recency_score = np.exp(-age / (7 * 24 * 3600))  # Decay over a week
            except Exception as e:
                Logger.warning(f"Recency calculation failed: {e}")
                recency_score = 0.0

            # Calculate chain bonus
            chain_bonus = 0.1 if context.metadata.get('parent_context') else 0

            # Combined score with weights
            final_score = (
                (1 - recency_weight) * semantic_score +  # Semantic similarity
                recency_weight * recency_score +         # Recency boost
                chain_bonus                              # Chain relationship bonus
            )

            # Get the best matching chunks for context
            matching_chunks = [
                context.compressed_tokens[i] for i in top_chunk_indices
            ]

            results.append((
                context,
                float(final_score),
                {
                    'chunks': matching_chunks,
                    'semantic_score': float(semantic_score),
                    'recency_score': float(recency_score),
                    'chain_bonus': chain_bonus
                }
            ))

        # Sort by final score and return top_k
        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
