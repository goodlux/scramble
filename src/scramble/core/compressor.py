from typing import Dict, List, Any, Optional
import uuid
import numpy as np
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
from .context import Context
from .stats import global_stats

import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)


class SemanticCompressor:
    """Core compression engine for semantic compression of text."""

    def __init__(self,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 128):

        nltk.download('punkt_tab')
        nltk.download('punkt') # Download the Punkt tokenizer for sentence splitting

        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size


    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into manageable chunks."""
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        current_speaker = None

        # Very aggressive chunk size adjustment
        text_length = len(text)
        if text_length < 100:  # Very short text
            adjusted_chunk_size = self.chunk_size
        elif text_length < 500:  # Medium text
            adjusted_chunk_size = 50
        else:  # Long text
            adjusted_chunk_size = min(20, text_length // 150)  # Much more aggressive for long texts

        print(f"Text length: {text_length}, Adjusted chunk size: {adjusted_chunk_size}")  # Debug print

        for line in lines:
            if line.startswith('Human: '):
                if current_chunk:
                    chunks.append({
                        'content': ' '.join(current_chunk),
                        'speaker': current_speaker,
                        'size': current_size
                    })
                    current_chunk = []
                    current_size = 0
                current_speaker = 'Human'
                line = line[7:]
            elif line.startswith('Assistant: '):
                if current_chunk:
                    chunks.append({
                        'content': ' '.join(current_chunk),
                        'speaker': current_speaker,
                        'size': current_size
                    })
                    current_chunk = []
                    current_size = 0
                current_speaker = 'Assistant'
                line = line[11:]

            line = line.strip()
            if not line:
                continue

            # Split more aggressively on sentence boundaries
            sentences = sent_tokenize(line)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Force a new chunk if:
                # 1. Current chunk is too big, or
                # 2. Adding this sentence would make it too big
                if (current_size >= adjusted_chunk_size or
                    current_size + len(sentence) > adjusted_chunk_size):
                    if current_chunk:
                        chunks.append({
                            'content': ' '.join(current_chunk),
                            'speaker': current_speaker,
                            'size': current_size
                        })
                    current_chunk = [sentence]
                    current_size = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_size += len(sentence)

        if current_chunk:
            chunks.append({
                'content': ' '.join(current_chunk),
                'speaker': current_speaker,
                'size': current_size
            })

        return chunks

    def _calculate_similarity(self, original_text: str, compressed_text: str) -> float:
        """Calculate semantic similarity between original and compressed text."""
        try:
            # Encode both texts
            original_embedding = self.model.encode(original_text, convert_to_numpy=True)
            compressed_embedding = self.model.encode(compressed_text, convert_to_numpy=True)

            # Calculate cosine similarity
            similarity = np.dot(original_embedding, compressed_embedding) / \
                        (np.linalg.norm(original_embedding) * np.linalg.norm(compressed_embedding))

            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity score: {e}")
            return 0.0

    def compress(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Context:
        """Compress text with enhanced metadata and stats tracking."""
        chunks = self._chunk_text(text)

        # Extract just the content strings from chunks for encoding
        chunk_texts = [chunk['content'] for chunk in chunks]

        # Generate embeddings
        embeddings = self.model.encode(chunk_texts, convert_to_numpy=True)

        # Calculate tokens and similarity
        original_tokens = len(text.split())
        compressed_text = ' '.join(chunk['content'] for chunk in chunks)
        compressed_tokens = len(compressed_text.split())

        # Calculate similarity score for stats
        similarity_score = self._calculate_similarity(text, compressed_text)

        # Generate context ID
        context_id = str(uuid.uuid4())

        # Record compression stats
        global_stats.record_compression(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            similarity_score=similarity_score,
            context_id=context_id
        )

        compression_metadata = {
            'original_length': len(text),
            'compressed_length': sum(len(c['content']) for c in chunks),
            'timestamp': datetime.utcnow().isoformat(),
            'compression_ratio': len(text) / sum(len(c['content']) for c in chunks),
            'semantic_similarity': similarity_score,
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            **(metadata or {})
        }

        # Create context with metadata
        return Context(
            id=context_id,
            embeddings=embeddings,
            compressed_tokens=chunks,
            metadata=compression_metadata
        )

    def find_similar(self,
                    query: str,
                    contexts: List[Context],
                    top_k: int = 3,
                    recency_weight: float = 0.1) -> List[tuple[Context, float, Dict[str, Any]]]:
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
                logger.warning(f"Recency calculation failed: {e}")
                recency_score = 0.0

            # Calculate chain bonus
            chain_bonus = 0.2 if context.metadata.get('parent_context') else 0

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
