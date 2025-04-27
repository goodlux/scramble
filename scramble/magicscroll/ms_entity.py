"""Entity extraction and management for MagicScroll."""
from typing import List, Set, Dict, Any, Optional
import re
from dataclasses import dataclass
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ExtractedEntity:
    """Represents an extracted entity with context."""
    name: str
    type: str  # 'mention', 'tag', 'noun_phrase', etc.
    context: str  # surrounding text
    confidence: float = 1.0

class EntityExtractor:
    """Extracts entities from conversation content."""
    
    # Common patterns for entity extraction
    PATTERNS = {
        'mentions': r'@(\w+)',           # @mentions
        'tags': r'#(\w+)',               # #hashtags
        'quotes': r'"([^"]+)"',          # "quoted phrases"
        'urls': r'https?://\S+',         # URLs
        'code_refs': r'`([^`]+)`',       # `code references`
        'key_terms': r'\*\*([^*]+)\*\*'  # **important terms**
    }

    def __init__(self):
        """Initialize with compiled regex patterns."""
        self.compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        }
        
    def extract_entities(self, content: str) -> List[ExtractedEntity]:
        """Extract entities from content using all available methods."""
        entities: List[ExtractedEntity] = []
        
        # Extract structured entities (mentions, tags, etc)
        entities.extend(self._extract_structured_entities(content))
        
        # Extract noun phrases (basic)
        entities.extend(self._extract_noun_phrases(content))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.name.lower() not in seen:
                seen.add(entity.name.lower())
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_structured_entities(self, content: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []
        
        for entity_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                # Get surrounding context (up to 50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                # Clean up the entity name
                entity_name = match.group(1) if match.groups() else match.group(0)
                entity_name = entity_name.strip()
                
                if entity_name:  # Ignore empty matches
                    entities.append(ExtractedEntity(
                        name=entity_name,
                        type=entity_type,
                        context=context,
                        confidence=1.0  # High confidence for pattern matches
                    ))
        
        return entities
    
    def _extract_noun_phrases(self, content: str) -> List[ExtractedEntity]:
        """
        Extract potential noun phrases using basic patterns.
        This is a simple implementation - could be enhanced with proper NLP.
        """
        entities = []
        
        # Simple capitalized phrases (2-3 words)
        cap_pattern = re.compile(r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})')
        matches = cap_pattern.finditer(content)
        
        for match in matches:
            phrase = match.group(0)
            # Get context
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end]
            
            entities.append(ExtractedEntity(
                name=phrase,
                type='noun_phrase',
                context=context,
                confidence=0.7  # Lower confidence for simple pattern matching
            ))
        
        return entities

class EntityManager:
    """Manages entity relationships and metadata."""
    
    def __init__(self, graph_manager):
        """Initialize with reference to graph manager."""
        self.graph = graph_manager
        self.extractor = EntityExtractor()
    
    async def process_content(
        self,
        content: str,
        entry_id: str,
        min_confidence: float = 0.7
    ) -> List[str]:
        """
        Process content to extract and store entities.
        Returns list of entity names that were processed.
        """
        # Extract entities
        extracted = self.extractor.extract_entities(content)
        
        # Filter by confidence
        valid_entities = [
            entity for entity in extracted
            if entity.confidence >= min_confidence
        ]
        
        # Get unique entity names
        entity_names = [entity.name for entity in valid_entities]
        
        if entity_names:
            # Create entity nodes and relationships
            await self.graph.create_entry_node(
                entry_id=entry_id,
                entities=entity_names
            )
        
        return entity_names