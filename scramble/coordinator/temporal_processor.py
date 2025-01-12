"""Utility for processing temporal references in messages."""
from typing import List, Dict, Any, Optional
import dateparser

class TemporalReference(Dict[str, Any]):
    """Type for temporal reference information."""
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

class TemporalProcessor:
    """Processes temporal references in messages."""
    
    @staticmethod
    def parse_temporal_references(content: str) -> List[TemporalReference]:
        """Parse temporal references from message content using dateparser."""
        # Simple words to ignore if they appear alone
        ignore_words = {'now', 'today', 'current', 'currently'}
        
        # Split content into potential temporal phrases
        words = content.split()
        temporal_refs: List[TemporalReference] = []
        
        for i in range(len(words)):
            # Try increasingly longer phrases
            for j in range(i + 1, min(i + 8, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                if phrase.lower() in ignore_words:
                    continue
                    
                parsed_date = dateparser.parse(
                    phrase,
                    settings={
                        'RETURN_AS_TIMEZONE_AWARE': False,
                        'PREFER_DATES_FROM': 'past'
                    }
                )
                
                if parsed_date:
                    temporal_refs.append(TemporalReference({
                        "type": "datetime",
                        "value": parsed_date,
                        "original_text": phrase
                    }))
                    break  # Found a valid date in this phrase, move to next starting word
                    
        return temporal_refs