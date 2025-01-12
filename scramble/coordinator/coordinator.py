"""Coordinator for model and scroll system.

TODO: 
- Implement proper user identification and tracking
- Replace hardcoded "User" recipient with actual user IDs
- Consider adding user session management
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
from scramble.utils.logging import get_logger
from .active_conversation import ActiveConversation
from .temporal_processor import TemporalProcessor
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
            logger.info("Core systems initialized")
        except Exception as e:
            logger.error(f"Failed to initialize core systems: {e}")
            raise

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

    async def provide_context_to_model(self, model_name: str) -> None:
        """Provide necessary context to a model that's newly addressed."""
        if not self.active_conversation:
            return

        missed_messages = self.active_conversation.get_context_for_model(model_name)
        if not missed_messages or not missed_messages:
            return

        # Format context for the model
        context = "Here's what you missed:\n"
        for msg in missed_messages:
            if msg.recipient:
                context += f"[{msg.timestamp.strftime('%H:%M')}] {msg.speaker} to {msg.recipient}: {msg.content}\n"
            else:
                context += f"[{msg.timestamp.strftime('%H:%M')}] {msg.speaker}: {msg.content}\n"

        if context != "Here's what you missed:\n":
            model = self.active_models[model_name]
            response = await model.generate_response(context)

            # Handle both string and async generator responses
            if isinstance(response, str):
                response_text = response
            else:
                response_chunks = []
                async for chunk in response:
                    response_chunks.append(chunk)
                response_text = "".join(response_chunks)

            if response_text:
                await self.active_conversation.add_message(
                    content=response_text,
                    speaker=model_name,
                    recipient="User"  # TODO: Replace with actual user ID
                )

    async def add_model_to_conversation(self, model_name: str) -> None:
        """Add a new model to the active set."""
        try:
            # Get model configuration
            config_manager = ConfigManager()
            model_config = await config_manager.get_model_config(model_name)
            provider = model_config.get("provider")
            
            logger.info(f"Loaded model: {model_config}")
            
            # Create appropriate model based on provider
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

    async def start_conversation(self) -> None:
        """Start a new conversation session."""
        self.active_conversation = ActiveConversation()
        for model_name in self.active_models:
            self.active_conversation.add_model(model_name)
        # Add system message for conversation start
        await self.active_conversation.add_message(
            content="Started new conversation session",
            speaker="system",
            recipient=None
        )
        logger.info("New conversation session started")

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.active_conversation:
                await self.start_conversation()

            if not self.scroll:
                raise RuntimeError("MagicScroll not initialized")

            if not self.active_conversation:
                raise RuntimeError("Failed to initialize conversation")

            if not self.active_models:
                raise RuntimeError("No active models available")

            # Find mentions anywhere in the message
            mentions = self.find_model_mentions(message)
            mentioned_model = mentions[0] if mentions else None

            # Get the model that should respond (mentioned or current speaker)
            responding_model = mentioned_model
            if not responding_model:
                # If no model mentioned, use current speaker or default to first model
                responding_model = list(self.active_models.keys())[0]

            # Add user message to conversation 
            await self.active_conversation.add_message(
                message, 
                speaker="user",
                recipient=mentioned_model
            )

            # If there's a mentioned model, provide context
            if mentioned_model:
                missed_context = self.active_conversation.get_context_for_model(mentioned_model)
                context = ""
                if missed_context:
                    context = "Previous messages in thread:\n"
                    for msg in missed_context:
                        if msg.recipient:
                            context += f"[{msg.timestamp.strftime('%H:%M')}] {msg.speaker} to {msg.recipient}: {msg.content}\n"
                        else:
                            context += f"[{msg.timestamp.strftime('%H:%M')}] {msg.speaker}: {msg.content}\n"
                    context += "\nCurrent message:\n"
                message = f"{context}{message}" if context else message

            # Generate response
            model = self.active_models[responding_model]
            response = await model.generate_response(message)
            
            # Process response
            if isinstance(response, str):
                response_text = response
            else:
                response_chunks = []
                async for chunk in response:
                    response_chunks.append(chunk)
                response_text = "".join(response_chunks)

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

    async def save_conversation_to_magicscroll(self) -> str:
        """Save the current conversation to MagicScroll storage."""
        return await self.end_conversation()

    async def end_conversation(self) -> str:
        """End the current conversation and save it to storage."""
        try:
            if not self.active_conversation or not self.scroll:
                raise RuntimeError("No active conversation to end")

            # Format and save the complete conversation
            formatted_conv = self.active_conversation.format_conversation_for_storage()
            metadata = ["conversation"]
            
            logger.info("=" * 50)
            logger.info("Saving conversation to MagicScroll...")
            logger.info(f"Active models: {', '.join(self.active_conversation.active_models)}")
            logger.info(f"Messages in conversation: {len(self.active_conversation.messages)}")
            
            entry_id = await self.scroll.write_conversation(
                content=formatted_conv,
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
