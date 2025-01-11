"""Coordinator for model and scroll system."""
from typing import Dict, List, Any, Optional
from datetime import timedelta
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
        self.conversation: Optional[ActiveConversation] = None
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

    async def _handle_add_model_request(self, message: str) -> Optional[str]:
        """Handle requests to add a new model to the conversation."""
        KNOWN_MODELS = {"sonnet", "opus", "haiku", "phi4", "granite"}  # Add all valid models
        
        # Direct command pattern checking
        message = message.lower().strip()
        words = message.split()
        
        # Look for model name after specific command words
        for i, word in enumerate(words):
            if word in {"add", "bring", "include", "invite"}:
                if i + 1 < len(words):
                    potential_model = words[i + 1].rstrip(",.!?")
                    if potential_model in KNOWN_MODELS:
                        return potential_model
                        
        # Check for complete phrases
        for model in KNOWN_MODELS:
            if f"add {model}" in message or \
               f"bring in {model}" in message or \
               f"include {model}" in message or \
               f"start chatting with {model}" in message:
                return model
                
        return None

    async def add_model(self, model_name: str) -> None:
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
            if self.conversation:
                self.conversation.add_model(model_name)
            logger.info(f"Added model: {model_name} (provider: {provider})")

        except Exception as e:
            logger.error(f"Failed to add model {model_name}: {e}")
            raise

    async def start_conversation(self) -> None:
        """Start a new conversation session."""
        self.conversation = ActiveConversation()
        for model_name in self.active_models:
            self.conversation.add_model(model_name)
        logger.info("New conversation session started")

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.conversation:
                await self.start_conversation()

            if not self.scroll:
                raise RuntimeError("MagicScroll not initialized")

            if not self.conversation:
                raise RuntimeError("Failed to initialize conversation")

            if not self.active_models:
                raise RuntimeError("No active models available")

            # Check if message is addressed to a specific model
            addressed_model, cleaned_message = self.conversation.parse_addressed_model(message)
            
            # If addressed to a model, check for model addition request
            if addressed_model:
                requested_model = await self._handle_add_model_request(cleaned_message)
                if requested_model:
                    try:
                        await self.add_model(requested_model)
                        response_text = f"Alright, {requested_model} is now in the loop. I'll keep an eye on things."
                        await self.conversation.add_message(
                            content=response_text,
                            speaker=addressed_model
                        )
                        return {
                            "response": response_text,
                            "model": addressed_model
                        }
                    except Exception as e:
                        error_msg = f"Hit a snag trying to bring in {requested_model}. Error: {str(e)}"
                        await self.conversation.add_message(
                            content=error_msg,
                            speaker=addressed_model
                        )
                        return {
                            "response": error_msg,
                            "model": addressed_model
                        }

            # Process temporal references
            temporal_refs = self.temporal_processor.parse_temporal_references(
                cleaned_message if addressed_model else message
            )
            
            if temporal_refs:
                logger.info(f"Found temporal references in message: {message}")
                for ref in temporal_refs:
                    logger.info(f"Temporal reference: type={ref['type']}, original_text='{ref['original_text']}', value={ref['value']}")

            # Add user message with temporal context
            await self.conversation.add_message(
                message, 
                speaker="user",
                metadata={"temporal_references": temporal_refs} if temporal_refs else None
            )

            # Simple temporal lookup for testing flow
            enhanced_prompt = cleaned_message if addressed_model else message
            if temporal_refs and self.scroll and self.scroll.doc_store:
                try:
                    logger.info("Attempting to retrieve recent entries from Redis...")
                    recent_entries = await self.scroll.get_recent(hours=24, limit=3)
                    if recent_entries:
                        logger.info(f"Found {len(recent_entries)} recent entries")
                        context_str = "\nRecent conversation context:\n"
                        for entry in recent_entries:
                            logger.info(f"Retrieved entry: {entry.content[:100]}...")
                        enhanced_prompt = f"{context_str}\n{enhanced_prompt}"
                        logger.info("Successfully enhanced prompt with historical context")
                    else:
                        logger.info("No recent entries found in Redis")
                except Exception as e:
                    logger.warning(f"Temporal lookup failed (skipping): {e}")

            # Get response from appropriate model
            if addressed_model and addressed_model in self.active_models:
                model = self.active_models[addressed_model]
                responding_model = addressed_model
            else:
                # Default to first available model
                responding_model = next(iter(self.active_models.keys()))
                model = self.active_models[responding_model]

            response = await model.generate_response(enhanced_prompt)

            # Process response
            if isinstance(response, str):
                response_text = response
            else:
                response_chunks = []
                async for chunk in response:
                    response_chunks.append(chunk)
                response_text = "".join(response_chunks)

            # Add model response to conversation
            await self.conversation.add_message(
                content=response_text,
                speaker=responding_model
            )

            # Return response with model name
            return {
                "response": response_text,
                "model": responding_model,
                "temporal_context": temporal_refs if temporal_refs else None
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def remove_model(self, model_name: str) -> None:
        """Remove a model from the active set."""
        if model_name in self.active_models:
            if self.conversation:
                self.conversation.remove_model(model_name)
            del self.active_models[model_name]
            logger.info(f"Removed model: {model_name}")

    def get_active_models(self) -> List[str]:
        """Get list of currently active model names."""
        return list(self.active_models.keys())

    async def end_conversation(self) -> str:
        """End the current conversation and save it to storage."""
        try:
            if not self.conversation or not self.scroll:
                raise RuntimeError("No active conversation to end")

            # Format and save the complete conversation
            formatted_conv = self.conversation.format_conversation_with_temporal()
            metadata = ["conversation"]
            
            # Add more visible logging for conversation saving
            logger.info("=" * 50)
            logger.info("Saving conversation to MagicScroll...")
            logger.info(f"Active models: {', '.join(self.conversation.active_models)}")
            logger.info(f"Messages in conversation: {len(self.conversation.messages)}")
            
            entry_id = await self.scroll.write_conversation(
                content=formatted_conv,
                metadata=metadata
            )
            
            logger.info(f"Conversation successfully saved with ID: {entry_id}")
            logger.info("=" * 50)

            # Clear the current conversation
            self.conversation = None

            return entry_id

        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            raise