"""Message context enrichment system."""
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
import re
from scramble.utils.logging import get_logger
from scramble.magicscroll.magic_scroll import MagicScroll
from scramble.magicscroll.ms_entry import EntryType
from .temporal_processor import TemporalProcessor, TemporalReference
from .active_conversation import MessageType

logger = get_logger(__name__)

@dataclass
class EnrichedContext:
    """Container for different types of enriched context."""
    topic_discussions: List[Dict[str, Any]] = field(default_factory=list)
    temporal_context: List[Dict[str, Any]] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def __len__(self) -> int:
        """Return the total length of context content."""
        total_length = 0
        
        # Add length of topic discussions
        for disc in self.topic_discussions:
            content = disc.get('content', '')
            total_length += len(content)
            
        # Add length of temporal context
        for entry in self.temporal_context:
            content = entry.get('content', '')
            total_length += len(content)
            
        return total_length
        
    def __bool__(self) -> bool:
        """Return True if there is any context content."""
        return bool(self.topic_discussions or self.temporal_context or self.related_concepts)

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
        
    async def enrich_message(self, message: str, active_conversation=None) -> EnrichedContext:
        """
        Analyze message and add relevant historical context.
        Returns enriched message text or None if no enrichment needed.
        """
        try:
            # Skip enrichment for system messages or very short queries
            if message.startswith("system:") or len(message.split()) < 3:
                return EnrichedContext()

            # Skip enrichment if scroll is not available
            if not self.scroll:
                logger.info("MagicScroll not available - skipping enrichment")
                return EnrichedContext()

            logger.info(f"Searching for context in message: {message}")

            context = EnrichedContext()
            memory_matches = self._check_memory_triggers(message)
            temporal_refs = self.temporal_processor.parse_temporal_references(message)
            
            logger.info(f"Found {len(memory_matches)} memory triggers")
            logger.info(f"Found {len(temporal_refs)} temporal references")

            if not memory_matches and not temporal_refs:
                logger.info("No triggers or temporal references found - skipping enrichment")
                return EnrichedContext()
                
            # Add topic context based on memory triggers
            if memory_matches:
                extracted_topics = self._extract_topics_from_matches(message, memory_matches)
                logger.debug(f"Extracted topics: {extracted_topics}")
                await self._add_topic_context(message, extracted_topics, context)
            
            # Add temporal context
            if temporal_refs:
                logger.debug(f"Found temporal references: {temporal_refs}")
                await self._add_temporal_context(temporal_refs, context)
            
            # If we found relevant context and have an active conversation, add the enriched context
            if (context.topic_discussions or context.temporal_context) and active_conversation:
                logger.debug(f"Found topic_discussion or temporal_context")
                await self._add_context_to_conversation(context, active_conversation)
            
            return context
            
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
            logger.info("Performing search_conversation with message")
            results = await self.scroll.search_conversation(
                message=message,
                limit=3
            )
            
            # If no results yet, that's expected during migration
            if not results:
                logger.info("No search results found - expected during migration")
                # Try direct search as fallback
                logger.info("Trying direct search as fallback")
                direct_results = await self.scroll.search(
                    query=message,
                    entry_types=[EntryType.CONVERSATION],
                    limit=3
                )
                if direct_results:
                    logger.info(f"Direct search found {len(direct_results)} results")
                    results = direct_results
                else:
                    logger.info("Direct search also found no results")
                    return
                
            logger.info(f"Found {len(results)} search results")
            # Log results in more detail but compact format
            logger.info(f"Found {len(results)} search results")
            for idx, result in enumerate(results[:3]):  # Limit to first 3 for brevity
                logger.info(f"Result {idx+1}:")
                # Extract the essentials (ID, timestamp, relevance)
                result_id = None
                timestamp = None
                score = None
                
                # Attempt to extract ID
                if hasattr(result, 'id'):
                    result_id = result.id
                elif isinstance(result, dict) and 'id' in result:
                    result_id = result['id']
                
                # Attempt to extract timestamp
                if hasattr(result, 'created_at'):
                    timestamp = result.created_at
                elif isinstance(result, dict) and 'created_at' in result:
                    timestamp = result['created_at']
                
                # Attempt to extract score/relevance
                if hasattr(result, 'score'):
                    score = result.score
                elif hasattr(result, 'distance'):
                    score = 1.0 - (float(result.distance) / 2.0)
                elif isinstance(result, dict):
                    if 'score' in result:
                        score = result['score']
                    elif 'distance' in result:
                        score = 1.0 - (float(result['distance']) / 2.0)
                
                logger.info(f"  ID: {result_id}")
                logger.info(f"  Timestamp: {timestamp}")
                score_str = f"{score:.4f}" if score is not None else "N/A"
                logger.info(f"  Score/Relevance: {score_str}")                
                
                # Get content preview if available
                content_preview = None
                if hasattr(result, 'content'):
                    content_preview = result.content[:50] + '...' if len(result.content) > 50 else result.content
                elif isinstance(result, dict) and 'content' in result:
                    content_preview = result['content'][:50] + '...' if len(result['content']) > 50 else result['content']
                elif hasattr(result, 'entity') and hasattr(result.entity, 'content'):
                    content_preview = result.entity.content[:50] + '...' if len(result.entity.content) > 50 else result.entity.content
                elif isinstance(result, dict) and 'entity' in result and isinstance(result['entity'], dict) and 'content' in result['entity']:
                    content_preview = result['entity']['content'][:50] + '...' if len(result['entity']['content']) > 50 else result['entity']['content']
                
                logger.info(f"  Content preview: {content_preview}")
                
                # Extract entry from result
                entry = None
                if hasattr(result, 'entry'):
                    entry = result.entry
                elif isinstance(result, dict) and 'entry' in result:
                    entry = result['entry']
                
                # Extract content from entry or result
                content = ""
                if entry and hasattr(entry, 'content'):
                    content = entry.content
                elif isinstance(entry, dict) and 'content' in entry:
                    content = entry['content']
                # Fallback to direct content on result
                elif hasattr(result, 'content'):
                    content = result.content
                elif isinstance(result, dict) and 'content' in result:
                    content = result['content']
                # Last resort, use preview
                elif content_preview:
                    content = content_preview
                # Get the result directly if it has the right structure
                elif hasattr(result, 'id') and hasattr(result, 'score'):
                    # This might be a direct hit from Milvus
                    content = str(result)
                
                logger.info(f"Content extraction: Found entry: {entry is not None}, Content length: {len(content) if content else 0}")
                
                if content and content not in seen_contents:
                    # Extract the entry ID if available
                    entry_id = None
                    if hasattr(result, 'id'):
                        entry_id = result.id
                    elif isinstance(result, dict) and 'id' in result:
                        entry_id = result['id']
                    elif hasattr(result, 'entry') and hasattr(result.entry, 'id'):
                        entry_id = result.entry.id
                    elif isinstance(result, dict) and 'entry' in result and isinstance(result['entry'], dict) and 'id' in result['entry']:
                        entry_id = result['entry']['id']
                    
                    context.topic_discussions.append({
                        'id': entry_id,
                        'entry': result,  # Store the full result for potential ID extraction later
                        'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                        'content': content,
                        'relevance': score,
                        'matched_topic': list(topics)[0] if topics else 'message context'
                    })
                    seen_contents.add(content)
                    logger.info(f"Added content to context: {len(content)} characters")
                    
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
                    
                    # Handle both object and dictionary result formats
                    content = ""
                    timestamp = None
                    score = 0.0
                    
                    # Case 1: SearchResult object with entry attribute
                    if hasattr(result, 'entry'):
                        entry = result.entry
                        if hasattr(entry, 'created_at'):
                            timestamp = entry.created_at
                        if hasattr(entry, 'content'):
                            content = entry.content
                        if hasattr(result, 'score'):
                            score = result.score
                        
                    # Case 2: Dictionary result (from simplified Milvus implementation)
                    elif isinstance(result, dict):
                        if 'created_at' in result:
                            # Handle both datetime object and string
                            if isinstance(result['created_at'], datetime):
                                timestamp = result['created_at']
                            else:
                                try:
                                    timestamp = datetime.fromisoformat(str(result['created_at']))
                                except Exception:
                                    timestamp = datetime.now(UTC)
                        
                        if 'content' in result:
                            content = result['content']
                        if 'score' in result:
                            score = result['score']
                            
                    # Case 3: Handle raw results from Milvus
                    elif hasattr(result, 'entity') and result.entity:
                        logger.info(f"Found entity-based result in temporal search")
                        entity = result.entity
                        if hasattr(entity, 'content'):
                            content = entity.content
                        elif hasattr(entity, 'orig_id') and hasattr(entity, 'content'):
                            content = entity.content
                        
                        if hasattr(entity, 'created_at'):
                            try:
                                timestamp = datetime.fromisoformat(str(entity.created_at))
                            except Exception:
                                timestamp = datetime.utcnow()
                        
                        if hasattr(result, 'distance'):
                            # Convert distance to score (smaller distance = higher score)
                            distance = result.distance
                            # Assuming distance is in range [0,2] as is typical with cosine distance
                            score = 1.0 - (float(distance) / 2.0)
                    
                    # Extract content for use in context
                    content = ""
                    if hasattr(result, 'content'):
                        content = result.content
                    elif isinstance(result, dict) and 'content' in result:
                        content = result['content']
                    elif hasattr(result, 'entity') and hasattr(result.entity, 'content'):
                        content = result.entity.content
                    elif isinstance(result, dict) and 'entity' in result and isinstance(result['entity'], dict) and 'content' in result['entity']:
                        content = result['entity']['content']
                    
                    if timestamp and content:
                        logger.info(f"  Timestamp: {timestamp}")
                        # Log first 100 chars of content
                        logger.info(f"  Content preview: {content[:100]}...")
                        
                        context.temporal_context.append({
                            'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                            'content': content,
                            'temporal_ref': ref['original_text']
                        })
                        
        except Exception as e:
            logger.error(f"Error adding temporal context: {e}")


    async def _add_context_to_conversation(self, context: EnrichedContext, active_conversation) -> None:
        """Add the enriched context to the active conversation as memory injections."""
        
        # Add topic-based discussions
        for disc in context.topic_discussions:
            # Format the memory content
            content = disc.get('content', '')
            matched_topic = disc.get('matched_topic', 'previous conversation')
            conversation_id = disc.get('id', 'unknown-id')
            
            # Add as a memory injection - properly await the coroutine
            await active_conversation.add_memory_injection(
                content=f"MEMORY ABOUT: {matched_topic}\n\n{content}",
                source_id=conversation_id
            )
            
        # Add temporal context
        for entry in context.temporal_context:
            # Format the memory content
            content = entry.get('content', '')
            temporal_ref = entry.get('temporal_ref', 'mentioned time period')
            temporal_id = entry.get('id', 'unknown-id')
            
            # Add as a memory injection - properly await the coroutine
            await active_conversation.add_memory_injection(
                content=f"MEMORY FROM: {temporal_ref}\n\n{content}",
                source_id=temporal_id
            )
    
    def _format_enriched_context(self, context: EnrichedContext, original_message: str) -> str:
        """Format the enriched context with the original message."""
        sections = []
        
        # Add topic-based discussions if available
        if context.topic_discussions:
            sections.append("\nSYSTEM MEMORY FROM PREVIOUS CONVERSATIONS:")
            # Sort discussions by relevance score (highest first)
            sorted_discussions = sorted(context.topic_discussions, key=lambda x: x.get('relevance', 0), reverse=True)
            
            # Log details of sorted discussions for debugging
            for idx, disc in enumerate(sorted_discussions):
                logger.debug(f"Discussion {idx+1}:")
                logger.debug(f"  Topic: {disc.get('matched_topic', 'unknown')}")
                logger.debug(f"  Relevance: {disc.get('relevance', 0):.2f}")
                logger.debug(f"  ID: {disc.get('id', 'None')}")
                logger.debug(f"  Has entry: {'entry' in disc}")
                if 'timestamp' in disc:
                    logger.debug(f"  Timestamp: {disc.get('timestamp')}")
                logger.debug(f"  Content length: {len(disc.get('content', ''))}")
            
            for idx, disc in enumerate(sorted_discussions):
                # Add an ID for easy reference
                conversation_id = disc.get('id', f"conv-{idx+1}")
                
                # Try to extract an actual ID from the entry
                if 'entry' in disc:
                    if hasattr(disc['entry'], 'id'):
                        conversation_id = disc['entry'].id
                    elif isinstance(disc['entry'], dict) and 'id' in disc['entry']:
                        conversation_id = disc['entry']['id']
                
                # Format the timestamp to be more readable
                try:
                    ts = None
                    # Try multiple sources for timestamp in this order of preference
                    if 'timestamp' in disc and disc['timestamp']:
                        ts = disc['timestamp']
                    elif hasattr(disc.get('entry', None), 'created_at'):
                        ts = disc['entry'].created_at
                    elif isinstance(disc.get('entry', None), dict) and 'created_at' in disc['entry']:
                        ts = disc['entry']['created_at']
                    elif hasattr(disc.get('entry', None), 'metadata') and hasattr(disc['entry'].metadata, 'get'):
                        ts = disc['entry'].metadata.get('created_at') or disc['entry'].metadata.get('timestamp')
                    elif isinstance(disc.get('entry', None), dict) and isinstance(disc['entry'].get('metadata', None), dict):
                        ts = disc['entry']['metadata'].get('created_at') or disc['entry']['metadata'].get('timestamp')
                    
                    # Convert to datetime if it's a string
                    if ts:
                        if isinstance(ts, str):
                            # Handle different ISO formats and timestamps
                            try:
                                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            except ValueError:
                                try:
                                    # Try parsing as a timestamp
                                    ts = datetime.fromtimestamp(float(ts))
                                except:
                                    # Give up and use current time
                                    ts = datetime.now()
                        formatted_time = ts.strftime("%Y-%m-%d %H:%M")
                    else:
                        formatted_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
                except Exception as e:
                    logger.debug(f"Error formatting timestamp: {e}")
                    formatted_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
                
                # Clean up the content to remove any system messages and extract user-model exchanges
                content = disc['content']
                conversation_extract = self._extract_relevant_exchanges(content, disc.get('matched_topic', ''))
                
                # If the conversation extract doesn't contain anything useful, try to extract from the
                # original vector search results
                if conversation_extract == "..." or not conversation_extract.strip() or len(conversation_extract) < 20:
                    logger.info("Insufficient conversation extract, trying to extract from vector search results directly")
                    
                    # Try to get the entry's content directly
                    if 'entry' in disc:
                        entry = disc['entry']
                        if hasattr(entry, 'content'):
                            content = entry.content
                            conversation_extract = self._extract_relevant_exchanges(content, disc.get('matched_topic', ''))
                        elif isinstance(entry, dict) and 'content' in entry:
                            content = entry['content']
                            conversation_extract = self._extract_relevant_exchanges(content, disc.get('matched_topic', ''))
                
                # Format the memory block clearly
                sections.append(f"""
===== MEMORY BLOCK {idx+1} =====
CONVERSATION ID: {conversation_id}
DATE: {formatted_time}
RELEVANCE: {disc.get('relevance', 0):.2f}
TOPIC: {disc.get('matched_topic', 'previous conversation')}
CONTENT:
{conversation_extract}
=============================""")
        
        # Add temporal context if available
        if context.temporal_context:
            sections.append("\nSYSTEM MEMORY FROM TIME PERIOD YOU MENTIONED:")
            for idx, entry in enumerate(context.temporal_context):
                # Add an ID for easy reference
                temporal_id = entry.get('id', f"time-{idx+1}")
                
                # Format the timestamp to be more readable
                formatted_time = entry.get('timestamp', 'unknown time')
                
                try:
                    if isinstance(formatted_time, str):
                        if formatted_time.endswith('Z'):
                            formatted_time = formatted_time[:-1]
                        ts = datetime.fromisoformat(formatted_time)
                        formatted_time = ts.strftime("%Y-%m-%d %H:%M")
                except Exception as e:
                    logger.debug(f"Error formatting temporal timestamp: {e}")
                    
                # Get content using our simplified extractor
                content = entry['content']
                conversation_extract = self._extract_relevant_exchanges(content, entry.get('temporal_ref', ''))
                    
                sections.append(f"""
===== MEMORY BLOCK FROM {entry.get('temporal_ref', 'mentioned time')} =====
MEMORY ID: {temporal_id}
DATE: {formatted_time}
CONTENT:
{conversation_extract}
=============================""")
        
        # Combine all context with original message
        if sections:
            context_str = "\n".join(sections)
            final_message = f"""=========== SYSTEM MEMORY INJECTION ===========
{context_str}

=========== CURRENT MESSAGE ===========
{original_message}
======================================="""
            logger.info("======================================================")
            logger.info("MEMORY CONTEXT BEING SENT TO MODEL:")
            logger.info(f"INCLUDES {len(context.topic_discussions)} TOPIC MEMORIES")
            logger.info(f"INCLUDES {len(context.temporal_context)} TEMPORAL MEMORIES")
            for i, disc in enumerate(context.topic_discussions):
                logger.info(f"MEMORY {i+1}: {disc.get('matched_topic', 'unknown')} (relevance: {disc.get('relevance', 0):.2f})")
                content_preview = disc['content'][:100] + '...' if len(disc['content']) > 100 else disc['content']
                logger.info(f"CONTENT PREVIEW: {content_preview}")
            logger.info("======================================================")
            return final_message
        
        return original_message
        
    def format_context_as_text(self, context: EnrichedContext, original_message: str) -> str:
        """Public method to format the context as text, useful for external callers."""
        return self._format_enriched_context(context, original_message)
        
    def _extract_relevant_exchanges(self, content: str, topic: str) -> str:
        """
        Extract context blocks from search results without trying to parse speakers.
        Simply provides the conversation content as memory injected by the system.
        """
        # For now, return the full context block rather than trying to parse it
        # We'll limit to a reasonable size to avoid overwhelming context
        max_chars = 2000  # Adjust this based on your context window
        
        # Truncate if necessary, preserving beginning and end for context
        if len(content) > max_chars:
            half_size = max_chars // 2
            result = content[:half_size] + "\n...[content trimmed]...\n" + content[-half_size:]
            logger.info(f"Returning truncated conversation content ({len(result)} chars)")
            return result
        
        logger.info(f"Returning full conversation content ({len(content)} chars)")
        return content