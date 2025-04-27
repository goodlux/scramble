"""Coordinator for model and scroll system."""
from typing import Dict, List, Any, Optional, Tuple, cast
from datetime import datetime, UTC
import re
import asyncio
from scramble.utils.logging import get_logger
from scramble.utils.context_debugger import context_debugger
from .active_conversation import ActiveConversation, MessageType
from .temporal_processor import TemporalProcessor
from .message_enricher import MessageEnricher
from scramble.magicscroll.magic_scroll import MagicScroll 
from ..model.llm_model_base import LLMModelBase
from scramble.model.anthropic_llm_model import AnthropicLLMModel
from scramble.model.ollama_llm_model import OllamaLLMModel
from scramble.model_config.config_manager import ConfigManager

logger = get_logger(__name__)

class Coordinator:
    """Coordinator for model and scroll system."""

    def __init__(self):
        """Initialize the coordination system."""
        self.magicscroll: Optional[MagicScroll] = None
        self.active_models: Dict[str, LLMModelBase] = {}
        self.active_conversation: Optional[ActiveConversation] = None
        self.temporal_processor = TemporalProcessor()
        self.message_enricher: Optional[MessageEnricher] = None

    @classmethod
    async def create(cls) -> 'Coordinator':
        """Create and initialize coordinator with better error handling."""
        coordinator = cls()
        
        try:
            # Check if MagicScroll is disabled
            import os
            is_magicscroll_disabled = os.environ.get('DISABLE_MAGICSCROLL', '0') == '1'
            
            if is_magicscroll_disabled:
                logger.info("MagicScroll disabled via environment variable")
                coordinator.magicscroll = None
            else:
                # Initialize core systems with timeout protection
                logger.info("Initializing MagicScroll...")
                
                # Try to initialize MagicScroll but don't let it block
                try:
                    # Create with timeout
                    coordinator.magicscroll = await asyncio.wait_for(
                        MagicScroll.create(),
                        timeout=10.0  # 10 second timeout
                    )
                    logger.info("MagicScroll initialized successfully")
                except asyncio.TimeoutError:
                    logger.warning("MagicScroll initialization timed out - continuing with limited functionality")
                    coordinator.magicscroll = None
                except Exception as e:
                    logger.error(f"MagicScroll initialization failed: {e}")
                    coordinator.magicscroll = None
            
            # Always create message enricher, even if MagicScroll failed
            logger.info("Creating MessageEnricher...")
            coordinator.message_enricher = MessageEnricher(
                coordinator.magicscroll, 
                coordinator.temporal_processor
            )
            
            logger.info("Core systems initialization complete")
            
        except Exception as e:
            logger.error(f"Critical error during coordinator initialization: {e}")
            # Continue with minimal functionality
            if not coordinator.message_enricher:
                coordinator.message_enricher = MessageEnricher(None, coordinator.temporal_processor)
        
        return coordinator


    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        # Handle debug commands
        if message.startswith('/debug'):
            return await self._handle_debug_command(message)
            
        try:
            if not self.active_conversation:
                await self.start_conversation()

            # Check only for message_enricher, MagicScroll can be None
            if not self.message_enricher:
                logger.warning("Message enricher not initialized, creating one now")
                self.message_enricher = MessageEnricher(None, self.temporal_processor)

            if not self.active_models:
                raise RuntimeError("No active models available")

            if not self.active_conversation:  # Type guard after start_conversation
                raise RuntimeError("Failed to initialize conversation")

            # Find mentions anywhere in the message
            mentions = self.find_model_mentions(message)
            mentioned_model = mentions[0] if mentions else None

            # If there's a mentioned model, they become the current speaker
            if mentioned_model:
                self.active_conversation.current_speaker = mentioned_model
                logger.debug(f"{mentioned_model} is now the current speaker")

            # Get the model that should respond
            responding_model = self._get_responding_model(mentioned_model)
            
            # Add user message to conversation
            user_message = await self.active_conversation.add_message(
                message,
                speaker="user",
                recipient=mentioned_model,
                message_type=MessageType.PERMANENT
            )
            
            # Save to FIPA storage if available
            if self.magicscroll and self.active_conversation.fipa_conversation_id:
                try:
                    self.magicscroll.save_fipa_message(
                        self.active_conversation.fipa_conversation_id,
                        "user",
                        mentioned_model or "all",
                        message,
                        "INFORM",
                        {"message_type": MessageType.PERMANENT.value, "message_id": user_message.message_id}
                    )
                except Exception as e:
                    logger.error(f"Failed to save user message to FIPA storage: {e}")

            # Build context for the model
            context = await self._build_model_context(
                message=message,
                model_name=responding_model,
                mentioned_model=mentioned_model
            )

            # Generate response
            model = self.active_models[responding_model]
            response = await model.generate_response(context)
            
            # Process response
            response_text = await self._process_model_response(response)

            # Add model response to conversation
            model_response = await self.active_conversation.add_message(
                content=response_text,
                speaker=responding_model,
                recipient="User",  # TODO: Replace with actual user ID
                message_type=MessageType.PERMANENT
            )
            
            # Save to FIPA storage if available
            if self.magicscroll and self.active_conversation.fipa_conversation_id:
                try:
                    self.magicscroll.save_fipa_message(
                        self.active_conversation.fipa_conversation_id,
                        responding_model,
                        "user",
                        response_text,
                        "INFORM",
                        {"message_type": MessageType.PERMANENT.value, "message_id": model_response.message_id}
                    )
                except Exception as e:
                    logger.error(f"Failed to save model response to FIPA storage: {e}")

            return {
                "response": response_text,
                "model": responding_model
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def _build_model_context(
        self,
        message: str,
        model_name: str,
        mentioned_model: Optional[str]
    ) -> str:
        """Build the complete context for the model's response."""
        if not self.active_conversation or not self.message_enricher:
            return message
            
        context_parts = []
        
        # Get conversation context if model was just mentioned
        if mentioned_model:
            missed_context = self.active_conversation.get_context_for_model(model_name)
            if missed_context:
                context_parts.append("Previous messages in thread:")
                for msg in missed_context:
                    if msg.recipient:
                        context_parts.append(
                            f"[{msg.timestamp.strftime('%H:%M')}] "
                            f"{msg.speaker} to {msg.recipient}: {msg.content}"
                        )
                    else:
                        context_parts.append(
                            f"[{msg.timestamp.strftime('%H:%M')}] "
                            f"{msg.speaker}: {msg.content}"
                        )

        # Get enriched historical context
        enriched_context = await self.message_enricher.enrich_message(message, self.active_conversation)
        if enriched_context and (enriched_context.topic_discussions or enriched_context.temporal_context):
            # Format the enriched context properly
            logger.info("===========================================================")
            logger.info("ENRICHED CONTEXT FROM SEARCH RESULTS FOUND - ADDING TO MODEL CONTEXT")
            logger.info(f"CONTEXT LENGTH: {len(enriched_context)} characters")
            logger.info("===========================================================")
            
            # Use the message enricher to format the context
            if self.message_enricher:
                formatted_context = self.message_enricher.format_context_as_text(enriched_context, message)
            else:
                # Fallback to our own formatting if message enricher isn't available
                formatted_context = self._format_enriched_context(enriched_context, message)
            
            # If we have missed conversation context, we need to combine it
            # with the enriched context
            if context_parts:
                # Combine conversation context with formatted enriched context
                conversation_context = "\n\n".join(context_parts)
                
                # Extract the original message part if possible
                parts = formatted_context.split("CURRENT MESSAGE:", 1)
                if len(parts) > 1:
                    # Combine conversation context with enriched context
                    enriched_prefix = parts[0]
                    original_message = parts[1].strip()
                    
                    # Build new combined context
                    complete_context = f"{conversation_context}\n\n{enriched_prefix}\nCURRENT MESSAGE:\n{original_message}"
                else:
                    # Fallback if we can't extract original message
                    complete_context = f"{conversation_context}\n\n{formatted_context}"
            else:
                # No conversation context, just use formatted enriched context
                complete_context = formatted_context
        else:
            # No enriched context, use original message with any conversation context
            logger.info("NO ENRICHED CONTEXT FOUND - USING ORIGINAL MESSAGE ONLY")
            context_parts.append(message)
            complete_context = "\n\n".join(context_parts)
        
        # Log the final complete context being sent to the model
        logger.info("===========================================================")
        logger.info("FINAL CONTEXT BEING SENT TO MODEL:")
        logger.info(f"- TOTAL LENGTH: {len(complete_context)} characters")
        logger.info("- PREVIEW: " + complete_context[:200] + "..." if len(complete_context) > 200 else complete_context)
        logger.info("===========================================================")
        
        # Record context for debugging
        context_debugger.record_context(
            context=complete_context,
            metadata={
                "model": model_name,
                "mentioned_model": mentioned_model,
                "timestamp": datetime.now(UTC).isoformat(),
                "query": message[:100] if len(message) > 100 else message  # Include the original query
            }
        )
        
        # Since we're now logging to files, we won't alter the context sent to the model
        return complete_context

    async def _process_model_response(self, response: Any) -> str:
        """Process model response into text."""
        if isinstance(response, str):
            return response
            
        # Handle streaming response
        response_chunks = []
        async for chunk in response:
            response_chunks.append(chunk)
        return "".join(response_chunks)
        
    def _format_enriched_context(self, enriched_context, original_message: str) -> str:
        """Format the enriched context with the original message."""
        sections = []
        
        # Add topic-based discussions if available
        if enriched_context.topic_discussions:
            sections.append("\nSYSTEM MEMORY FROM PREVIOUS CONVERSATIONS:")
            # Sort discussions by relevance score (highest first)
            sorted_discussions = sorted(enriched_context.topic_discussions, 
                                        key=lambda x: x.get('relevance', 0), 
                                        reverse=True)
            
            for idx, disc in enumerate(sorted_discussions):
                # Format the memory block clearly
                conversation_id = disc.get('id', f"conv-{idx+1}")
                timestamp = disc.get('timestamp', 'unknown time')
                matched_topic = disc.get('matched_topic', 'previous conversation')
                content = disc.get('content', '')
                
                sections.append(f"""
===== MEMORY BLOCK {idx+1} =====
CONVERSATION ID: {conversation_id}
DATE: {timestamp}
RELEVANCE: {disc.get('relevance', 0):.2f}
TOPIC: {matched_topic}
CONTENT:
{content}
=============================""")
        
        # Add temporal context if available
        if enriched_context.temporal_context:
            sections.append("\nSYSTEM MEMORY FROM TIME PERIOD YOU MENTIONED:")
            for idx, entry in enumerate(enriched_context.temporal_context):
                # Add an ID for easy reference
                temporal_id = entry.get('id', f"time-{idx+1}")
                timestamp = entry.get('timestamp', 'unknown time')
                temporal_ref = entry.get('temporal_ref', 'mentioned time period')
                content = entry.get('content', '')
                
                sections.append(f"""
===== MEMORY BLOCK FROM {temporal_ref} =====
MEMORY ID: {temporal_id}
DATE: {timestamp}
CONTENT:
{content}
=============================""")
        
        # Combine all context with original message
        if sections:
            context_str = "\n".join(sections)
            final_message = f"""=========== SYSTEM MEMORY INJECTION ===========
{context_str}

=========== CURRENT MESSAGE ===========
{original_message}
======================================="""
            return final_message
        
        return original_message

    def _get_responding_model(self, mentioned_model: Optional[str]) -> str:
        """Determine which model should respond."""
        if mentioned_model:
            return mentioned_model
            
        # If no model mentioned, use current speaker or default to first model
        if self.active_conversation and self.active_conversation.current_speaker:
            return self.active_conversation.current_speaker
            
        responding_model = list(self.active_models.keys())[0]
        if self.active_conversation:
            self.active_conversation.current_speaker = responding_model
            logger.debug(f"{responding_model} is now the current speaker (default)")
        return responding_model

    def find_model_mentions(self, message: str) -> List[str]:
        """Find all @model mentions in a message."""
        mentions = []
        words = message.split()
        for word in words:
            if word.startswith('@'):
                model_name = word[1:].lower()
                # Case-insensitive model name lookup
                for active_model in self.active_models:
                    if active_model.lower() == model_name:
                        mentions.append(active_model)
        return mentions

    async def start_conversation(self) -> None:
        """Start a new conversation session."""
        self.active_conversation = ActiveConversation()
        
        # Create FIPA conversation in MagicScroll if available
        if self.magicscroll:
            try:
                # Create a new FIPA conversation
                conversation_id = self.magicscroll.create_fipa_conversation({
                    "start_time": datetime.now(UTC).isoformat(),
                    "active_models": list(self.active_models.keys())
                })
                
                # Set the FIPA conversation ID in active conversation
                self.active_conversation.fipa_conversation_id = conversation_id
                logger.info(f"FIPA conversation created with ID: {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to create FIPA conversation: {e}")
        
        # Add models to the conversation
        for model_name in self.active_models:
            self.active_conversation.add_model(model_name)
            
        # Add system message for conversation start
        if self.active_conversation:  # Type guard
            await self.active_conversation.add_message(
                content="Started new conversation session",
                speaker="system",
                recipient=None,
                message_type=MessageType.PERMANENT
            )
            
            # Save the system message to FIPA storage if available
            if self.magicscroll and self.active_conversation.fipa_conversation_id:
                try:
                    self.magicscroll.save_fipa_message(
                        self.active_conversation.fipa_conversation_id,
                        "system",
                        "all",
                        "Started new conversation session",
                        "INFORM",
                        {"message_type": MessageType.PERMANENT.value}
                    )
                except Exception as e:
                    logger.error(f"Failed to save system message to FIPA storage: {e}")
                    
            logger.info("New conversation session started")

    async def add_model_to_conversation(self, model_name: str) -> None:
        """Add a new model to the active set."""
        try:
            config_manager = ConfigManager()
            model_config = await config_manager.get_model_config(model_name)
            provider = model_config.get("provider")
            
            logger.info(f"Loaded model: {model_config}")
            
            if provider == "anthropic":
                model = await AnthropicLLMModel.create(model_name)
            elif provider == "ollama":
                model = await OllamaLLMModel.create(model_name)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            self.active_models[model_name] = model
            if self.active_conversation:
                self.active_conversation.add_model(model_name)
                await self.active_conversation.add_message(
                    content=f"{model_name} was added to the conversation",
                    speaker="system",
                    recipient=None
                )
            logger.info(f"Added model: {model_name} (provider: {provider})")

        except Exception as e:
            logger.error(f"Failed to add model {model_name}: {e}")
            raise

    async def remove_model_from_conversation(self, model_name: str) -> None:
        """Remove a model from the active set."""
        if model_name in self.active_models:
            if self.active_conversation:
                await self.active_conversation.add_message(
                    content=f"{model_name} was removed from the conversation",
                    speaker="system",
                    recipient=None
                )
                self.active_conversation.remove_model(model_name)
            del self.active_models[model_name]
            logger.info(f"Removed model: {model_name}")

    def get_active_models(self) -> List[str]:
        """Get list of currently active model names."""
        return list(self.active_models.keys())

    async def _handle_debug_command(self, message: str) -> Dict[str, Any]:
        """Handle debug commands for context visibility."""
        try:
            # Check for specific debug commands
            if message.strip() == '/debug context' or message.strip() == '/debug':
                # Just inform about context logging
                return {
                    "response": f"Context is being logged to disk in: ~/repos/scramble/logs/context_dumps/\nCheck this directory for context dump files.",
                    "model": "system"
                }
                
            # Default response for unrecognized commands
            return {
                "response": "Context logging is active. Check ~/repos/scramble/logs/context_dumps/ for context dumps.",
                "model": "system"
            }
            
        except Exception as e:
            logger.error(f"Error handling debug command: {e}")
            return {
                "response": f"Error processing debug command: {str(e)}",
                "model": "system"
            }

    async def save_conversation_to_magicscroll(self) -> Optional[str]:
        """Save the current conversation to MagicScroll storage."""
        try:
            # Check for active conversation
            if not self.active_conversation:
                logger.warning("No active conversation to save")
                return None
                
            # Check for MagicScroll
            if not self.magicscroll:
                logger.warning("MagicScroll not available - conversation will not be saved")
                return None

            # If we have a FIPA conversation ID, save using FIPA flow
            if self.active_conversation.fipa_conversation_id:
                try:
                    # Close the FIPA conversation
                    self.magicscroll.close_fipa_conversation(self.active_conversation.fipa_conversation_id)
                    
                    # Get metadata about the conversation
                    metadata = {
                        "models": list(self.active_conversation.active_models),
                        "start_time": self.active_conversation.start_time.isoformat(),
                        "end_time": datetime.now(UTC).isoformat(),
                        "message_count": len(self.active_conversation.messages)
                    }
                    
                    # Save to MagicScroll (which will filter appropriately)
                    entry_id = await self.magicscroll.save_fipa_conversation_to_ms(
                        self.active_conversation.fipa_conversation_id, metadata
                    )
                    
                    logger.info(f"FIPA conversation saved with ID: {entry_id}")
                    
                    # Reset active conversation
                    self.active_conversation = None
                    return entry_id
                    
                except Exception as e:
                    logger.error(f"Error saving FIPA conversation: {e}")
                    # Fall back to traditional save
            
            # Default: Create conversation entry the traditional way
            from scramble.magicscroll.ms_entry import MSConversation
            conversation = MSConversation(
                content=self.active_conversation.format_conversation(),
                metadata={
                    "start_time": self.active_conversation.start_time.isoformat(),
                    "end_time": datetime.now(UTC).isoformat()
                }
            )
            
            # Try to save
            try:
                logger.info("Saving conversation to MagicScroll...")
                entry_id = await self.magicscroll.save_ms_entry(conversation)
                logger.info(f"Conversation saved with ID: {entry_id}")
                
                # Reset conversation
                self.active_conversation = None
                return entry_id
                
            except Exception as save_err:
                logger.error(f"Error saving to MagicScroll: {save_err}")
                return None

        except Exception as e:
            logger.error(f"Error preparing conversation for save: {e}")
            return None
