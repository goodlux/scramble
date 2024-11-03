# src/scramble/core/context.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime

@dataclass
class Context:
    """Represents a compressed conversation context."""
    id: str
    embeddings: np.ndarray
    compressed_tokens: List[str]
    metadata: Dict[str, any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def size(self) -> int:
        """Return the size of the compressed context in tokens."""
        return len(self.compressed_tokens)
    
    def merge(self, other: 'Context') -> 'Context':
        """Merge this context with another, returning a new Context."""
        # Simple concatenation for now - we'll make this smarter later
        return Context(
            id=f"{self.id}_{other.id}",
            embeddings=np.concatenate([self.embeddings, other.embeddings]),
            compressed_tokens=self.compressed_tokens + other.compressed_tokens,
            metadata={
                **self.metadata,
                **other.metadata,
                'merged_from': [self.id, other.id]
            }
        )

# src/scramble/core/compressor.py
from typing import List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from .context import Context
import uuid

class SemanticCompressor:
    """Core compression engine for semantic compression of text."""
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 512):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into manageable chunks for embedding."""
        # This is a simple implementation - we'll make it smarter later
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) > self.chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word)
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks
    
    def compress(self, text: str, context_id: Optional[str] = None) -> Context:
        """Compress text into a semantic representation."""
        # Split into chunks and embed
        chunks = self._chunk_text(text)
        embeddings = self.model.encode(chunks)
        
        return Context(
            id=context_id or str(uuid.uuid4()),
            embeddings=embeddings,
            compressed_tokens=chunks,  # For now, just store chunks - we'll add real compression later
            metadata={
                'original_length': len(text),
                'chunk_count': len(chunks),
                'model_name': self.model.get_sentence_embedding_dimension()
            }
        )
    
    def find_similar(self, query: str, contexts: List[Context], top_k: int = 3) -> List[Tuple[Context, float]]:
        """Find the most similar contexts to a query."""
        query_embedding = self.model.encode([query])[0]
        
        similarities = []
        for context in contexts:
            # Use max similarity across all chunks
            chunk_similarities = np.dot(context.embeddings, query_embedding)
            max_similarity = np.max(chunk_similarities)
            similarities.append((context, float(max_similarity)))
        
        # Sort by similarity and return top_k
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

# src/scramble/core/store.py
from typing import Dict, List, Optional
from pathlib import Path
import json
import numpy as np
from .context import Context
import pickle

class ContextStore:
    """Manages storage and retrieval of compressed contexts."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or Path.home() / '.ramble' / 'store')
        self.contexts: Dict[str, Context] = {}
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_contexts()
    
    def _load_contexts(self) -> None:
        """Load all contexts from storage."""
        for context_file in self.storage_path.glob('*.pkl'):
            with open(context_file, 'rb') as f:
                context = pickle.load(f)
                self.contexts[context.id] = context
    
    def add(self, context: Context) -> None:
        """Store a compressed context."""
        self.contexts[context.id] = context
        # Save to disk
        with open(self.storage_path / f"{context.id}.pkl", 'wb') as f:
            pickle.dump(context, f)
    
    def get(self, context_id: str) -> Optional[Context]:
        """Retrieve a context by ID."""
        return self.contexts.get(context_id)
    
    def list(self) -> List[Context]:
        """List all stored contexts."""
        return list(self.contexts.values())
    
    def merge(self, context_ids: List[str]) -> Optional[Context]:
        """Merge multiple contexts into a new one."""
        contexts = [self.contexts.get(cid) for cid in context_ids]
        if not all(contexts) or len(contexts) < 2:
            return None
            
        result = contexts[0]
        for other in contexts[1:]:
            result = result.merge(other)
        
        self.add(result)
        return result