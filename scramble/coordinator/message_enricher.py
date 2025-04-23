"""Message context enrichment system."""
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
from scramble.utils.logging import get_logger
from scramble.magicscroll.magic_scroll import MagicScroll
from scramble.magicscroll.ms_entry import EntryType
from .temporal_processor import TemporalProcessor, TemporalReference

logger = get_logger(__name__)

@dataclass
class EnrichedContext:
    """Container for different types of enriched context."""
    topic_discussions: List[Dict[str, Any]] = field(default_factory=list)
    temporal_context: List[Dict[str, Any]] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

class MessageEnricher:
    """Enriches messages with relevant historical context."""
    
    # Comprehensive trigger patterns
    MEMORY_PATTERNS = [
        # Direct recall requests
        r"remember (?:when|how|what|why|that)",
        r"recall (?:when|how|what|why|that)",
        
        # Discussion references
        r"(?:we|you) (?:talked|discussed|mentioned|said|wrote) about",
        r"(?:we|you) were (?:talking|discussing|saying) about",
        r"(?:earlier|previous|before) (?:conversation|discussion|chat)",
        
        # Time-based references
        r"last (?:time|conversation|week|month)",
        r"(?:a while|some time) ago",
        r"(?:earlier|previously|before) (?:today|this week|this month)",
        
        # Topic continuity
        r"(?:going|getting) back to",
        r"(?:as|like) (?:we|you) (?:mentioned|discussed|talked about)",
        r"(?:follow(?:ing)? up|continuing) (?:on|from|with)",
        
        # Indirect references
        r"(?:what|how) did (?:we|you) (?:decide|conclude|determine)",
        r"(?:remind|tell) me (?:about|what)",
        r"(?:that|the) thing (?:we|you) (?:talked|discussed) about"
    ]
    
    def __init__(self, magic_scroll: Optional[MagicScroll], temporal_processor: TemporalProcessor):
        """Initialize with required components."""
        self.scroll = magic_scroll
        self.temporal_processor = temporal_processor
        # Compile regex patterns for efficiency
        self.memory_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.MEMORY_PATTERNS]
        
        # Log the initialization state
        if self.scroll is None:
            logger.warning("MessageEnricher initialized without MagicScroll - memory features disabled")
        else:
            logger.info("MessageEnricher initialized with MagicScroll")
        
    async def enrich_message(self, message: str) -> Optional[str]:
        """
        Analyze message and add relevant historical context.
        Returns enriched message text or None if no enrichment needed.
        """
        try:
            # Skip enrichment for system messages or very short queries
            if message.startswith("system:") or len(message.split()) < 3:
                return None

            # Skip enrichment if scroll is not available
            if not self.scroll:
                logger.info("MagicScroll not available - skipping enrichment")
                return None

            logger.info(f"Searching for context in message: {message}")

            context = EnrichedContext()
            memory_matches = self._check_memory_triggers(message)
            temporal_refs = self.temporal_processor.parse_temporal_references(message)
            
            logger.info(f"Found {len(memory_matches)} memory triggers")
            logger.info(f"Found {len(temporal_refs)} temporal references")

            if not memory_matches and not temporal_refs:
                logger.info("No triggers or temporal references found - skipping enrichment")
                return None
                
            # Add topic context based on memory triggers
            if memory_matches:
                extracted_topics = self._extract_topics_from_matches(message, memory_matches)
                logger.debug(f"Extracted topics: {extracted_topics}")
                await self._add_topic_context(message, extracted_topics, context)
            
            # Add temporal context
            if temporal_refs:
                logger.debug(f"Found temporal references: {temporal_refs}")
                await self._add_temporal_context(temporal_refs, context)
            
            # If we found relevant context, format and return it
            if context.topic_discussions or context.temporal_context:
                logger.debug(f"Found topic_discussion or temporal_context")
                return self._format_enriched_context(context, message)
            
            return None
            
        except Exception as e:
            logger.error(f"Error enriching message: {e}")
            return None
    
    def _check_memory_triggers(self, message: str) -> List[Tuple[str, re.Match]]:
        """Check for memory trigger patterns and return matches with their patterns."""
        matches = []
        for pattern in self.memory_patterns:
            found = pattern.search(message)
            if found:
                logger.info(f"Memory trigger matched: {pattern.pattern}")
                logger.info(f"Match text: {found.group(0)}")
                matches.append((pattern.pattern, found))
        return matches
    
    def _extract_topics_from_matches(self, message: str, matches: List[Tuple[str, re.Match]]) -> Set[str]:
        """Extract relevant topics from the memory trigger matches."""
        topics = set()
        for pattern, match in matches:
            # Get the text after the trigger
            post_trigger = message[match.end():].strip()
            
            # Split into words and take a reasonable chunk
            words = post_trigger.split()
            if words:
                # Take up to 5 words after the trigger as potential topic
                topic = ' '.join(words[:5])
                topics.add(topic)
        
        return topics
    
    async def _add_topic_context(
        self,
        message: str,
        topics: Set[str],
        context: EnrichedContext
    ) -> None:
        """Add topic-based context from previous discussions."""
        try:
            # Skip if scroll is not available
            if not self.scroll:
                logger.info("MagicScroll not available - skipping topic context")
                return
                
            seen_contents = set()  # Avoid duplicate content
            
            # Use direct search method since we're going through a transition
            logger.info(f"Searching for topics: {topics}")
            logger.info(f"Search query: {message}")
            
            # Use search conversation method instead of going through index
            results = await self.scroll.search_conversation(
                message=message,
                limit=3
            )
            
            # If no results yet, that's expected during migration
            if not results:
                logger.info("No search results found - expected during migration")
                return
                
            logger.info(f"Found {len(results)} search results")
            for idx, result in enumerate(results):
                logger.info(f"Result {idx+1}:")
                if hasattr(result, 'score'):
                    logger.info(f"  Score: {result.score}")
                if hasattr(result, 'entry') and hasattr(result.entry, 'created_at'):
                    logger.info(f"  Timestamp: {result.entry.created_at}")
                    # Log first 100 chars of content
                    content_preview = result.entry.content[:100] if hasattr(result.entry, 'content') else "No content"
                    logger.info(f"  Content preview: {content_preview}...")
                    
                    if result.entry.content not in seen_contents:
                        context.topic_discussions.append({
                            'timestamp': result.entry.created_at.isoformat(),
                            'content': result.entry.content,
                            'relevance': getattr(result, 'score', 0.0),
                            'matched_topic': list(topics)[0] if topics else 'message context'
                        })
                        seen_contents.add(result.entry.content)
                    
        except Exception as e:
            logger.error(f"Error adding topic context: {e}")
    
    async def _add_temporal_context(
        self,
        temporal_refs: List[TemporalReference],
        context: EnrichedContext
    ) -> None:
        """Add context from specific time periods."""
        try:
            # Skip if scroll is not available
            if not self.scroll:
                logger.info("MagicScroll not available - skipping temporal context")
                return
                
            for ref in temporal_refs:
                ref_time = ref['value']
                # Add a reasonable window around the reference time
                window = timedelta(hours=12)  # Adjustable window
                
                temporal_filter = {
                    'start': ref_time - window,
                    'end': ref_time + window
                }
                
                logger.info(f"Temporal search:")
                logger.info(f"  Reference: {ref['original_text']}")
                logger.info(f"  Time window: {temporal_filter['start']} to {temporal_filter['end']}")
                
                # Use direct search method with temporal filtering
                results = await self.scroll.search(
                    query="",  # Empty query to match all in timeframe
                    entry_types=[EntryType.CONVERSATION],
                    temporal_filter=temporal_filter,
                    limit=3
                )
                
                # If no results yet, that's expected during migration
                if not results:
                    logger.info("No temporal results found - expected during migration")
                    continue
                
                logger.info(f"Found {len(results)} temporal results")
                for idx, result in enumerate(results):
                    logger.info(f"Result {idx+1}:")
                    if hasattr(result, 'entry') and hasattr(result.entry, 'created_at'):
                        logger.info(f"  Timestamp: {result.entry.created_at}")
                        
                        # Get content safely with attribute checks
                        content = "No content"
                        if hasattr(result, 'entry') and hasattr(result.entry, 'content'):
                            content = result.entry.content
                            # Log first 100 chars of content
                            logger.info(f"  Content preview: {content[:100]}...")
                        
                        context.temporal_context.append({
                            'timestamp': result.entry.created_at.isoformat(),
                            'content': content,
                            'temporal_ref': ref['original_text']
                        })
                        
        except Exception as e:
            logger.error(f"Error adding temporal context: {e}")


    def _format_enriched_context(self, context: EnrichedContext, original_message: str) -> str:
        """Format the enriched context with the original message."""
        sections = []
        
        # Add topic-based discussions if available
        if context.topic_discussions:
            sections.append("\nRelevant previous discussions:")
            for disc in context.topic_discussions:
                sections.append(f"""
    When: {disc['timestamp']}
    Matched on: {disc.get('matched_topic', 'context')}
    {disc['content']}
    ---""")
        
        # Add temporal context if available
        if context.temporal_context:
            sections.append("\nFrom the time period you mentioned:")
            for entry in context.temporal_context:
                sections.append(f"""
    {entry['temporal_ref']}: {entry['timestamp']}
    {entry['content']}
    ---""")
        
        # Combine all context with original message
        if sections:
            context_str = "\n".join(sections)
            final_message = f"""Context from previous conversations:{context_str}

    Current message:
    {original_message}"""
            logger.info("Enriched context being injected:")
            logger.info("-" * 50)
            logger.info(final_message)
            logger.info("-" * 50)
            return final_message
        
        return original_message