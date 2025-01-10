from typing import Dict, List, Any, Optional
from scramble.utils.logging import get_logger
from .active_conversation import ActiveConversation
from scramble.magicscroll.magic_scroll import MagicScroll 
from ..model.llm_model_base import LLMModelBase
from scramble.model.anthropic_llm_model import AnthropicLLMModel

logger = get_logger(__name__)

class Coordinator:
    """Coordinator for model and scroll system."""

    def __init__(self):
        """Initialize the coordination system."""
        self.scroll: Optional[MagicScroll] = None
        self.active_models: Dict[str, LLMModelBase] = {}
        self.conversation: Optional[ActiveConversation] = None

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

    async def add_model(self, model_name: str) -> None:
        """Add a new model to the active set."""
        try:
            model = await AnthropicLLMModel.create(model_name)
            self.active_models[model_name] = model

            if self.conversation:
                self.conversation.add_model(model_name)

            logger.info(f"Added model: {model_name}")

        except Exception as e:
            logger.error(f"Failed to add model {model_name}: {e}")
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

    async def start_conversation(self) -> None:
        """Start a new conversation session."""
        self.conversation = ActiveConversation()
        for model_name in self.active_models:
            self.conversation.add_model(model_name)

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.conversation:
                await self.start_conversation()

            if not self.scroll:
                raise RuntimeError("MagicScroll not initialized")

            if not self.conversation:
                raise RuntimeError("Failed to initialize conversation")

            await self.conversation.add_message(message, speaker="user")

            if not self.active_models:
                raise RuntimeError("No active models available")

            model_name = next(iter(self.active_models.keys()))
            model = self.active_models[model_name]

            response = await model.generate_response(message)

            if isinstance(response, str):
                response_text = response
            else:
                response_chunks = []
                async for chunk in response:
                    response_chunks.append(chunk)
                response_text = "".join(response_chunks)

            await self.conversation.add_message(
                content=response_text,
                speaker=model_name
            )

            formatted_conv = self.conversation.format_conversation()
            metadata = ["conversation"]
            entry_id = await self.scroll.write_conversation(
                content=formatted_conv,
                metadata=metadata
            )

            self.conversation.current_entry_id = entry_id

            return {
                "response": response_text,
                "model": model_name,
                "entry_id": entry_id
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise