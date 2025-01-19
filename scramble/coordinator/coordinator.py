"""Coordinator for model and scroll system."""
from typing import Dict, List, Any, Optional, Tuple, cast
from datetime import datetime
import re
from scramble.utils.logging import get_logger
from .active_conversation import ActiveConversation
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
        self.scroll: Optional[MagicScroll] = None
        self.active_models: Dict[str, LLMModelBase] = {}
        self.active_conversation: Optional[ActiveConversation] = None
        self.temporal_processor = TemporalProcessor()
        self.message_enricher: Optional[MessageEnricher] = None

    @classmethod
    async def create(cls) -> 'Coordinator':
        """Factory method to create and initialize coordinator."""
        coordinator = cls()
        await coordinator.initialize()
        return coordinator

    async def initialize(self) -> None:
        """Initialize the coordinator."""
        try:
            self.scroll = await MagicScroll.create()
            # Initialize message enricher with MagicScroll and TemporalProcessor
            if self.scroll:  # Type guard
                self.message_enricher = MessageEnricher(self.scroll, self.temporal_processor)
                logger.info("Core systems initialized")
        except Exception as e:
            logger.error(f"Failed to initialize core systems: {e}")
            raise

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.active_conversation:
                await self.start_conversation()

            if not self.scroll or not self.message_enricher:
                raise RuntimeError("Core systems not initialized")

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
            await self.active_conversation.add_message(
                message,
                speaker="user",
                recipient=mentioned_model
            )

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
            await self.active_conversation.add_message(
                content=response_text,
                speaker=responding_model,
                recipient="User"  # TODO: Replace with actual user ID
            )

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
        enriched_context = await self.message_enricher.enrich_message(message)
        if enriched_context:
            context_parts.append(enriched_context)
        else:
            context_parts.append(message)

        return "\n\n".join(context_parts)

    async def _process_model_response(self, response: Any) -> str:
        """Process model response into text."""
        if isinstance(response, str):
            return response
            
        # Handle streaming response
        response_chunks = []
        async for chunk in response:
            response_chunks.append(chunk)
        return "".join(response_chunks)

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
        for model_name in self.active_models:
            self.active_conversation.add_model(model_name)
        # Add system message for conversation start
        if self.active_conversation:  # Type guard
            await self.active_conversation.add_message(
                content="Started new conversation session",
                speaker="system",
                recipient=None
            )
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

    async def end_conversation(self) -> str:
        """End the current conversation and save it to storage."""
        try:
            if not self.active_conversation or not self.scroll:
                raise RuntimeError("No active conversation to end")

            # Format and save the complete conversation
            conv_data = self.active_conversation.format_conversation_for_storage()
            
            # Create proper metadata from conversation data
            metadata = {
                "type": "conversation",
                "start_time": conv_data["start_time"],
                "active_models": conv_data["active_models"],
                # Add any other useful metadata
                "message_count": len(conv_data["messages"]),
                "participants": list({msg["speaker"] for msg in conv_data["messages"]})
            }
            
            # Convert message data to string format for storage
            content = self.active_conversation.format_conversation()
            
            logger.info("=" * 50)
            logger.info("Saving conversation to MagicScroll...")
            logger.info(f"Active models: {', '.join(self.active_conversation.active_models)}")
            logger.info(f"Messages in conversation: {len(self.active_conversation.messages)}")
            
            entry_id = await self.scroll.write_conversation(
                content=content,
                metadata=metadata
            )
            
            logger.info(f"Conversation successfully saved with ID: {entry_id}")
            logger.info("=" * 50)

            # Clear the current conversation
            self.active_conversation = None

            return entry_id

        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            raise

    async def save_conversation_to_magicscroll(self) -> str:
        """Save the current conversation to MagicScroll storage."""
        return await self.end_conversation()