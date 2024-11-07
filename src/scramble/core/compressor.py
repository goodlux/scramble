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
import os
import zipfile

# NTLK tokenizer data path settings
nltk_data_path = './data/nltk_data'
# Define the path to the punkt.zip zipped data file
punkt_tab_zip_file = './data/nltk_data/tokenizers/punkt_tab.zip'

# Extract the punkt.zip file if it hasn't been extracted yet
if not os.path.exists(os.path.join(nltk_data_path, 'tokenizers', 'punkt_tab')):
    with zipfile.ZipFile(punkt_zip_file, 'r') as zip_ref:
        zip_ref.extractall(nltk_data_path)

# Set the NLTK data path to the directory where you extracted the punkt data
nltk.data.path.append(nltk_data_path)

logger = logging.getLogger(__name__)

class CompressionLevel:
    """Compression level settings."""
    LOW = {
        'chunk_size': 128,
        'min_sentence_length': 10,
        'semantic_threshold': 0.8,
        'text_length_multiplier': 1.0  # For dynamic chunk size adjustment
    }
    MEDIUM = {
        'chunk_size': 64,
        'min_sentence_length': 5,
        'semantic_threshold': 0.7,
        'text_length_multiplier': 0.75
    }
    HIGH = {
        'chunk_size': 32,
        'min_sentence_length': 3,
        'semantic_threshold': 0.6,
        'text_length_multiplier': 0.5
    }

class SemanticCompressor:
    """Core compression engine for semantic compression of text."""

    def __init__(self,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 128):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
        self.set_compression_level('MEDIUM')  # Default to medium compression

    def set_compression_level(self, level: str):
        """Set compression parameters based on level."""
        if level not in ['LOW', 'MEDIUM', 'HIGH']:
            raise ValueError(f"Unknown compression level: {level}")

        settings = getattr(CompressionLevel, level)
        self.chunk_size = settings['chunk_size']
        self.min_sentence_length = settings['min_sentence_length']
        self.semantic_threshold = settings['semantic_threshold']
        self.text_length_multiplier = settings['text_length_multiplier']
        logger.debug(f"Set compression level to {level}: {settings}")

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into manageable chunks with compression settings."""
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        current_speaker = None

        # Dynamic chunk size based on text length and compression settings
        text_length = len(text)
        if text_length < 100:  # Very short text
            adjusted_chunk_size = self.chunk_size
        elif text_length < 500:  # Medium text
            adjusted_chunk_size = int(self.chunk_size * self.text_length_multiplier)
        else:  # Long text
            adjusted_chunk_size = min(
                int(self.chunk_size * self.text_length_multiplier),
                text_length // 150
            )


        # def split_into_sentences(text: str) -> List[str]:## Previous tokenizer, leaving here for reference temporarily.
        #     """Simple sentence splitter using common punctuation."""
        #     segments = []
        #     current = []

        #     for i, char in enumerate(text):
        #         current.append(char)
        #         if char in '.!?' and (i + 1 >= len(text) or text[i + 1].isspace()):
        #             if len(''.join(current).strip()) >= self.min_sentence_length:
        #                 segments.append(''.join(current).strip())
        #             current = []

        #     if current and len(''.join(current).strip()) >= self.min_sentence_length:
        #         segments.append(''.join(current).strip())

        #     return [s for s in segments if s]

        # for line in lines:
        #     if line.startswith('Human: '):
        #         if current_chunk:
        #             chunks.append({
        #                 'content': ' '.join(current_chunk),
        #                 'speaker': current_speaker,
        #                 'size': current_size
        #             })
        #             current_chunk = []
        #             current_size = 0
        #         current_speaker = 'Human'
        #         line = line[7:]
        #     elif line.startswith('Assistant: '):
        #         if current_chunk:
        #             chunks.append({
        #                 'content': ' '.join(current_chunk),
        #                 'speaker': current_speaker,
        #                 'size': current_size
        #             })
        #             current_chunk = []
        #             current_size = 0
        #         current_speaker = 'Assistant'
        #         line = line[11:]

        #     line = line.strip()
        #     if not line:
        #         continue

        #     sentences = split_into_sentences(line)
        #     for sentence in sentences:
        #         sentence = sentence.strip()
        #         if not sentence:
        #             continue

        #         if (current_size >= adjusted_chunk_size or
        #             current_size + len(sentence) > adjusted_chunk_size):
        #             if current_chunk:
        #                 chunks.append({
        #                     'content': ' '.join(current_chunk),
        #                     'speaker': current_speaker,
        #                     'size': current_size
        #                 })
        #             current_chunk = [sentence]
        #             current_size = len(sentence)
        #         else:
        #             current_chunk.append(sentence)
        #             current_size += len(sentence)

        # if current_chunk:
        #     chunks.append({
        #         'content': ' '.join(current_chunk),
        #         'speaker': current_speaker,
        #         'size': current_size
        #     })

        # return chunks

        def split_into_sentences(text: str) -> List[str]:
            """Use NLTK's sentence tokenizer to split text into sentences."""
            sentences = sent_tokenize(text)
            return [s for s in sentences if len(s.strip()) >= self.min_sentence_length]

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

            sentences = split_into_sentences(line)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

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
        chunks = self._chunk_text(text)
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
            'timestamp': datetime.utcnow().isoformat(),
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
