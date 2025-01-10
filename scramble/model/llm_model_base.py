"""Enhanced base class for Scramble's LLM models with temporal context handling."""
from typing import Dict, Any, AsyncGenerator, Union, List, Literal, TypedDict, Optional
from datetime import datetime, timedelta
import asyncio
import time
import logging
import re
from abc import ABC, abstractmethod
from .model_base import ModelBase
from ..model_config.config_manager import ConfigManager 
from ..magicscroll.magic_scroll import MagicScroll
from ..magicscroll.ms_entry import MSEntry

logger = logging.getLogger(__name__)

# Type definitions for message handling
Role = Literal["user", "assistant", "system"]

class Message(TypedDict):
    """Type for standardized message format."""
    role: Role
    content: str
    timestamp: str
    metadata: Dict[str, Any]

class TemporalReference(TypedDict):
    """Type for temporal reference information."""
    type: Literal["absolute", "relative", "duration"]
    value: Union[datetime, timedelta]
    original_text: str

class LLMModelBase(ModelBase):
    """Base class adding Scramble-specific features to LLM models."""
    
    # Class attributes with type annotations
    model_name: str
    model_id: Optional[str]
    config: Dict[str, Any]
    rate_limit: float
    _last_request: float
    max_context_length: int
    context_buffer: List[Message]
    system_message: Optional[str]
    magic_scroll: Optional[MagicScroll]

    def __init__(self):
        """Basic initialization only. Use create() instead."""
        super().__init__()
        # Initialize all class attributes
        self.model_name = ""
        self.model_id = None
        self.config = {}
        self.rate_limit = 2.0
        self._last_request = 0.0
        self.max_context_length = 4096
        self.context_buffer = []
        self.system_message = None
        self.magic_scroll = None

    def _trim_context_if_needed(self) -> None:
        """Trim context buffer if it exceeds max length."""
        max_messages = self.config.get("max_context_messages", 10)
        if len(self.context_buffer) > max_messages:
            if self.system_message:
                system_message: Message = {
                    "role": "system",
                    "content": self.system_message,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {}
                }
                self.context_buffer = (
                    [system_message] +
                    self.context_buffer[-(max_messages-1):]
                )
            else:
                self.context_buffer = self.context_buffer[-max_messages:]

    @classmethod
    async def create(cls, model_name: str) -> "LLMModelBase":
        """Create and initialize a new model instance."""
        self = cls()
        
        # Basic setup
        self.model_name = model_name
        self.model_id = None
        self.config = {}
        self.rate_limit = 2.0
        self._last_request = 0.0
        self.max_context_length = 4096
        self.context_buffer = []
        self.system_message = None
        
        # Initialize MagicScroll for memory access
        self.magic_scroll = await MagicScroll.create()
        
        # Load config and initialize client
        try:
            config_manager = ConfigManager()
            self.config = await config_manager.get_model_config(self.model_name)
            self.model_id = self.config["model_id"]
            await self._initialize_client()
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            raise
            
        return self

    def _parse_temporal_references(self, content: str) -> List[TemporalReference]:
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
                    try:
                        # Handle different date formats
                        date_value = self._parse_absolute_date(original_text)
                        if date_value:
                            references.append({
                                "type": "absolute",
                                "value": date_value,
                                "original_text": original_text
                            })
                    except ValueError:
                        continue
                        
                elif ref_type == "relative":
                    value = self._parse_relative_reference(original_text)
                    if value:
                        references.append({
                            "type": "relative",
                            "value": value,
                            "original_text": original_text
                        })
                        
                elif ref_type == "duration":
                    duration = self._parse_duration_reference(original_text)
                    if duration:
                        references.append({
                            "type": "duration",
                            "value": duration,
                            "original_text": original_text
                        })
        
        return references

    async def _retrieve_temporal_context(self, references: List[TemporalReference]) -> List[MSEntry]:
        """Retrieve relevant historical context based on temporal references."""
        if not self.magic_scroll:
            return []
        
        context_entries = []
        
        for ref in references:
            try:
                if ref["type"] == "duration":
                    # For durations, get entries within the time period
                    duration = ref["value"]
                    if isinstance(duration, timedelta):
                        hours = int(duration.total_seconds() / 3600)
                        recent_entries = await self.magic_scroll.get_recent(hours=hours)
                        context_entries.extend(recent_entries)
                        
                elif ref["type"] in ["absolute", "relative"]:
                    # For absolute/relative times, search around that time
                    target_time = ref["value"]
                    if isinstance(target_time, datetime):
                        # Search within a window around the target time
                        window_hours = 24  # Configurable window
                        start_time = target_time - timedelta(hours=window_hours/2)
                        end_time = target_time + timedelta(hours=window_hours/2)
                        
                        # Use temporal search capability
                        query = f"timestamp:[{start_time.isoformat()} TO {end_time.isoformat()}]"
                        results = await self.magic_scroll.search(
                            query=query,
                            limit=5
                        )
                        context_entries.extend(results)  # Results are already MSEntry objects
            
            except Exception as e:
                logger.warning(f"Error retrieving temporal context for reference {ref}: {e}")
                continue
        
        return context_entries

    def _add_to_context(
        self,
        role: Role,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to the context buffer with temporal reference handling."""
        # Parse temporal references
        temporal_refs = self._parse_temporal_references(content)
        
        # Create message with enhanced metadata
        message: Message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                **(metadata or {}),
                "temporal_references": [
                    {
                        "type": ref["type"],
                        "reference": ref["original_text"],
                        "timestamp": ref["value"].isoformat() if isinstance(ref["value"], datetime) else str(ref["value"])
                    }
                    for ref in temporal_refs
                ]
            }
        }
        
        self.context_buffer.append(message)
        self._trim_context_if_needed()

    async def _inject_temporal_context(self, prompt: str) -> str:
        """Inject relevant temporal context into the prompt."""
        temporal_refs = self._parse_temporal_references(prompt)
        if not temporal_refs:
            return prompt
            
        # Retrieve relevant historical context
        context_entries = await self._retrieve_temporal_context(temporal_refs)
        
        if not context_entries:
            return prompt
            
        # Format context entries
        context_str = "\nRelevant historical context:\n"
        for entry in context_entries:
            context_str += f"- {entry.content}\n"
            
        # Inject context before the prompt
        return f"{context_str}\n{prompt}"

    @abstractmethod
    async def _initialize_client(self) -> None:
        """Initialize provider-specific client."""
        raise NotImplementedError

    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs: Any) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response from the model."""
        raise NotImplementedError
        
    def _parse_absolute_date(self, date_str: str) -> Optional[datetime]:
        """Parse absolute date references."""
        try:
            # Add more date format handling as needed
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
            
    def _parse_relative_reference(self, ref_str: str) -> Optional[datetime]:
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
            
        # Handle "X days/weeks/months/years ago"
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
        
    def _parse_duration_reference(self, ref_str: str) -> Optional[timedelta]:
        """Parse duration references."""
        # Handle "last/past X hours/days/weeks/months/years"
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