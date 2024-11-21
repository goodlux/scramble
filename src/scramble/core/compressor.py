from typing import Dict, List, Any, Optional
import uuid
import numpy as np
from datetime import datetime, UTC
import logging
from sentence_transformers import SentenceTransformer
from .context import Context
from .stats import global_stats
import nltk
from nltk.tokenize import sent_tokenize
import os
import zipfile

# Download NLTK tokenizer data // punkt_tab deprecated use punkt instead
nltk.download('punkt_tab')

logger = logging.getLogger(__name__)

class CompressionLevel:
    """Compression level settings."""
    LOW = {
        'chunk_size': 265,           # Much larger chunks
        'min_sentence_length': 15,   # Longer sentences
        'semantic_threshold': 0.95,  # Higher similarity requirement
        'text_length_multiplier': 0.9,
        'combine_threshold': 0.8     # More likely to combine chunks
    }
    MEDIUM = {
        'chunk_size': 64,           # Medium chunks
        'min_sentence_length': 5,    # Medium sentences
        'semantic_threshold': 0.7,
        'text_length_multiplier': 0.75,
        'combine_threshold': 0.7
    }
    HIGH = {
        'chunk_size': 16,            # Very small chunks #
        'min_sentence_length': 2,    # Short sentences
        'semantic_threshold': 0.3,  # Lower threshold
        'text_length_multiplier': 0.25, # Very aggressive
        'combine_threshold': 0.4
    }

# 1.
# Notes: Lowered LOW semantic threshold .95 -> .9, text_length_multiplier .9 -> .7 = more meaningful chunks,
# Notes: HIGH Compression, dropped chunk size to 32->16, 0.27->.25 text_length_multiplier, semantic_threshold 0.4 -> 0.3 = greater compression
# Notes: No changes to MEDIUM
# No changes to test, stil failing.


class SemanticCompressor:
    """Core compression engine for semantic compression of text."""

    def __init__(self,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 128):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
        self.set_compression_level('MEDIUM')  # Default to medium compression

    def _handle_short_text(self, cleaned_lines: List[str]) -> List[Dict[str, Any]]:
        """Process short text into a single chunk."""
        current_speaker = None
        content_parts = []

        for line in cleaned_lines:
            if line.startswith('Human: '):
                current_speaker = 'Human'
                content_parts.append(line[7:])
            elif line.startswith('Assistant: '):
                current_speaker = 'Assistant'
                content_parts.append(line[11:])
            else:
                content_parts.append(line)

        content = ' '.join(content_parts)
        return [{
            'content': content,
            'speaker': current_speaker,
            'size': len(content)
        }]

    def set_compression_level(self, level: str):
        """Set compression parameters based on level."""
        if level not in ['LOW', 'MEDIUM', 'HIGH']:
            raise ValueError(f"Unknown compression level: {level}")

        settings = getattr(CompressionLevel, level)
        self.chunk_size = settings['chunk_size']
        self.min_sentence_length = settings['min_sentence_length']
        self.semantic_threshold = settings['semantic_threshold']
        self.text_length_multiplier = settings['text_length_multiplier']
        self.combine_threshold = settings['combine_threshold']
        logger.debug(f"Set compression level to {level}: {settings}")


    def _should_combine_chunks(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> bool:
        """Determine if two chunks should be combined based on compression level."""
        # Don't combine across speakers
        if chunk1['speaker'] != chunk2['speaker']:
            return False

        combined_size = chunk1['size'] + chunk2['size']

        # Size check based on compression level
        if combined_size > self.chunk_size * (2 - self.text_length_multiplier):
            return False

        # Similarity check
        similarity = self._calculate_similarity(
            chunk1['content'],
            chunk2['content']
        )

        return similarity >= self.combine_threshold

    def split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting based on compression level."""
        sentences = []
        current = []

        for i, char in enumerate(text):
            current.append(char)

            # Check for sentence boundaries based on compression level
            if char in '.!?' and len(''.join(current).strip()) >= self.min_sentence_length:
                # HIGH compression: split more aggressively
                if self.text_length_multiplier <= 0.25:
                    sentences.append(''.join(current).strip())
                    current = []
                # MEDIUM compression: normal sentence splits
                elif self.text_length_multiplier <= 0.5:
                    next_char = text[i + 1] if i + 1 < len(text) else ' '
                    if next_char.isspace():
                        sentences.append(''.join(current).strip())
                        current = []
                # LOW compression: only split on clear sentence boundaries
                else:
                    next_char = text[i + 1] if i + 1 < len(text) else ' '
                    if next_char.isspace() and not any(
                        text[i+2:i+6].startswith(x) for x in ['and', 'or', 'but']
                    ):
                        sentences.append(''.join(current).strip())
                        current = []

        if current:
            sentences.append(''.join(current).strip())

        return [s for s in sentences if s]

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text with enhanced compression control."""
        if not text or not text.strip():
            return []

        text = text.strip()
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        chunks = []  # Define chunks at the main function level

        # Short text handling
        is_short = (
            len(cleaned_lines) <= 3 and
            len(text) < 300 and
            any(line.startswith(('Human:', 'Assistant:'))
                for line in cleaned_lines)
        )

        if is_short:
            return self._handle_short_text(cleaned_lines)

        current_chunk = {
            'content': [],
            'speaker': None,
            'size': 0
        }

        def save_current_chunk():
            """Helper to save current chunk if not empty."""
            if current_chunk['content']:
                chunks.append({
                    'content': ' '.join(current_chunk['content']),
                    'speaker': current_chunk['speaker'],
                    'size': current_chunk['size']
                })
                current_chunk['content'] = []
                current_chunk['size'] = 0
                # Keep the same speaker

        for line in cleaned_lines:
            # Handle speaker changes
            if line.startswith('Human: '):
                save_current_chunk()
                current_chunk['speaker'] = 'Human'
                line = line[7:]
            elif line.startswith('Assistant: '):
                save_current_chunk()
                current_chunk['speaker'] = 'Assistant'
                line = line[11:]

            line = line.strip()
            if not line:
                continue

            # Process sentences
            sentences = self.split_into_sentences(line)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Check if we need to start a new chunk
                if (current_chunk['size'] >= self.chunk_size or
                    current_chunk['size'] + len(sentence) > self.chunk_size):
                    save_current_chunk()

                current_chunk['content'].append(sentence)
                current_chunk['size'] += len(sentence)

        # Save final chunk if needed
        save_current_chunk()

        # Optimize chunks if needed based on compression level
        if len(chunks) > 1:
            optimized_chunks = []
            current = None

            for chunk in chunks:
                if not current:
                    current = chunk
                    continue

                if self._should_combine_chunks(current, chunk):
                    # Combine chunks
                    current['content'] += ' ' + chunk['content']
                    current['size'] += chunk['size']
                else:
                    optimized_chunks.append(current)
                    current = chunk

            if current:
                optimized_chunks.append(current)

            return optimized_chunks

        return chunks

    def _calculate_similarity(self, original_text: str, compressed_text: str) -> float:
        """Calculate semantic similarity between original and compressed text."""
        try:
            original_embedding = self.model.encode(original_text, convert_to_numpy=True)
            compressed_embedding = self.model.encode(compressed_text, convert_to_numpy=True)

            similarity = np.dot(original_embedding, compressed_embedding) / \
                        (np.linalg.norm(original_embedding) * np.linalg.norm(compressed_embedding))

            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity score: {e}")
            return 0.0

    def compress(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Context:
        """Compress text with enhanced metadata and stats tracking."""

        if not text or not text.strip():
            logger.warning("Received empty or whitespace-only text for compression")
            return Context(
                id=str(uuid.uuid4()),
                embeddings=np.array([]),
                compressed_tokens=[],
                metadata={'error': 'empty_input'}
            )

        chunks = self._chunk_text(text)

        # Guard against no valid chunks
        if not chunks:
            logger.warning("No valid chunks produced during compression")
            return Context(
                id=str(uuid.uuid4()),
                embeddings=np.array([]),
                compressed_tokens=[{'content': text, 'speaker': None, 'size': len(text)}],
                metadata={'error': 'no_chunks_produced'}
            )

        compressed_length = sum(len(c['content']) for c in chunks)

        # Guard against zero compressed length
        if compressed_length == 0:
            logger.warning("Compressed content length is zero")
            return Context(
                id=str(uuid.uuid4()),
                embeddings=np.array([]),
                compressed_tokens=[{'content': text, 'speaker': None, 'size': len(text)}],
                metadata={'error': 'zero_compressed_length'}
            )


        chunk_texts = [chunk['content'] for chunk in chunks]
        embeddings = self.model.encode(chunk_texts, convert_to_numpy=True)

        # Calculate tokens and similarity
        original_tokens = len(text.split())
        compressed_text = ' '.join(chunk['content'] for chunk in chunks)
        compressed_tokens = len(compressed_text.split())
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
            'timestamp': datetime.now(UTC).isoformat(),
            'compression_ratio': len(text) / sum(len(c['content']) for c in chunks),
            'semantic_similarity': similarity_score,
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            **(metadata or {})
        }

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

        query_embedding = self.model.encode(query, convert_to_numpy=True)
        now = datetime.utcnow()

        results = []

        for context in contexts:
            chunk_similarities = np.dot(context.embeddings, query_embedding)
            top_chunk_indices = np.argsort(chunk_similarities)[-3:]
            top_chunk_scores = chunk_similarities[top_chunk_indices]
            semantic_score = np.mean(top_chunk_scores)

            try:
                timestamp = context.metadata.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                elif timestamp is None:
                    timestamp = now

                age = (now - timestamp).total_seconds()
                recency_score = np.exp(-age / (7 * 24 * 3600))
            except Exception as e:
                logger.warning(f"Recency calculation failed: {e}")
                recency_score = 0.0

            chain_bonus = 0.2 if context.metadata.get('parent_context') else 0

            final_score = (
                (1 - recency_weight) * semantic_score +
                recency_weight * recency_score +
                chain_bonus
            )

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

        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
