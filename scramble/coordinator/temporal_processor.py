"""Utility for processing temporal references in messages."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

class TemporalReference(Dict[str, Any]):
    """Type for temporal reference information."""
    pass

class TemporalProcessor:
    """Processes temporal references in messages."""
    
    @staticmethod
    def parse_temporal_references(content: str) -> List[TemporalReference]:
        """Parse temporal references from message content."""
        references: List[TemporalReference] = []
        
        # Common time patterns
        patterns = {
            # Absolute dates
            r"(\d{4}-\d{2}-\d{2})": "absolute",
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*(?:\d{4})?": "absolute",
            
            # Relative references
            r"(yesterday|last week|last month|previous month|last year)": "relative",
            r"(\d+)\s+(day|week|month|year)s?\s+ago": "relative",
            
            # Duration references
            r"(?:in|over|during|for)\s+(?:the\s+)?(?:last|past)\s+(\d+)\s+(hour|day|week|month|year)s?": "duration",
            r"(?:in|over|during|for)\s+(?:the\s+)?(?:last|past)\s+(hour|day|week|month|year)": "duration"
        }
        
        for pattern, ref_type in patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                original_text = match.group(0)
                
                if ref_type == "absolute":
                    date_value = TemporalProcessor._parse_absolute_date(original_text)
                    if date_value:
                        references.append({
                            "type": "absolute",
                            "value": date_value,
                            "original_text": original_text
                        })
                        
                elif ref_type == "relative":
                    value = TemporalProcessor._parse_relative_reference(original_text)
                    if value:
                        references.append({
                            "type": "relative",
                            "value": value,
                            "original_text": original_text
                        })
                        
                elif ref_type == "duration":
                    duration = TemporalProcessor._parse_duration_reference(original_text)
                    if duration:
                        references.append({
                            "type": "duration",
                            "value": duration,
                            "original_text": original_text
                        })
        
        return references

    @staticmethod
    def _parse_absolute_date(date_str: str) -> Optional[datetime]:
        """Parse absolute date references."""
        try:
            formats = [
                "%Y-%m-%d",
                "%B %d %Y",
                "%B %d, %Y",
                "%B %dst %Y",
                "%B %dnd %Y",
                "%B %drd %Y",
                "%B %dth %Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            return None
            
        except Exception:
            return None

    @staticmethod
    def _parse_relative_reference(ref_str: str) -> Optional[datetime]:
        """Parse relative time references."""
        now = datetime.now()
        
        if ref_str.lower() == "yesterday":
            return now - timedelta(days=1)
            
        if ref_str.lower() == "last week":
            return now - timedelta(weeks=1)
            
        if ref_str.lower() == "last month":
            return now - timedelta(days=30)
            
        if ref_str.lower() == "last year":
            return now - timedelta(days=365)
            
        match = re.match(r"(\d+)\s+(day|week|month|year)s?\s+ago", ref_str, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            
            if unit == "day":
                return now - timedelta(days=num)
            elif unit == "week":
                return now - timedelta(weeks=num)
            elif unit == "month":
                return now - timedelta(days=num * 30)
            elif unit == "year":
                return now - timedelta(days=num * 365)
                
        return None

    @staticmethod
    def _parse_duration_reference(ref_str: str) -> Optional[timedelta]:
        """Parse duration references."""
        match = re.search(r"(\d+)?\s*(hour|day|week|month|year)s?", ref_str, re.IGNORECASE)
        if match:
            num = int(match.group(1)) if match.group(1) else 1
            unit = match.group(2).lower()
            
            if unit == "hour":
                return timedelta(hours=num)
            elif unit == "day":
                return timedelta(days=num)
            elif unit == "week":
                return timedelta(weeks=num)
            elif unit == "month":
                return timedelta(days=num * 30)
            elif unit == "year":
                return timedelta(days=num * 365)
                
        return None