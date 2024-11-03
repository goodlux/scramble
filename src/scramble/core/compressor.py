from typing import Dict, List, Any, Optional
import uuid
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from .context import Context

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
    
    def compress(self, 
                text: str, 
                context_id: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None) -> Context:
        """Compress text into a semantic representation."""
        # Split into chunks and get their content
        chunks = self._chunk_text(text)
        chunk_texts = [chunk['content'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.model.encode(chunk_texts, convert_to_numpy=True)
        
        # Create context with metadata
        return Context(
            id=context_id or str(uuid.uuid4()),
            embeddings=embeddings,
            compressed_tokens=chunks,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def find_similar(self, 
                    query: str, 
                    contexts: List[Context],
                    top_k: int = 3) -> List[tuple[Context, float, Dict[str, Any]]]:
        """Find contexts and chunks most similar to query."""
        if not contexts:
            return []
        
        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        results = []
        for context in contexts:
            # Calculate similarity with each chunk
            similarities = np.dot(context.embeddings, query_embedding)
            max_sim_idx = np.argmax(similarities)
            max_similarity = float(similarities[max_sim_idx])
            
            # Get the best matching chunk
            matching_chunk = context.compressed_tokens[max_sim_idx]
            
            results.append((context, max_similarity, matching_chunk))
        
        # Sort by similarity
        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]