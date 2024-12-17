"""Core coordination system for Scramble."""
from typing import Optional, Dict, Any, Set
import logging
from pathlib import Path
from datetime import datetime

from .active_conversation import ActiveConversation, ConversationMessage
from ..model.other_llm_model import OtherLLMModel
from ..magicscroll.magic_scroll import MagicScroll

logger = logging.getLogger(__name__)

class Coordinator:
    """Coordinator for model and scroll system."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the coordination system."""
        self.config = config or {}
        self.scroll = None
        self.models: Dict[str, OtherLLMModel] = {}
        self.conversation: Optional[ActiveConversation] = None
        
        # Initialize core systems
        self._initialize_systems()
    
    def _initialize_systems(self) -> None:
        """Initialize core subsystems."""
        try:
            # Initialize Magic Scroll
            storage_path = Path(self.config.get("storage_path", "~/.ramble")).expanduser()
            self.scroll = MagicScroll(storage_path=storage_path)
            
            # Initialize default model
            self.initialize_model(
                model_type=self.config.get("default_model", "claude-3-sonnet")
            )
            
            logger.info("Core systems initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize core systems: {e}")
            raise
    
    def initialize_model(self, model_type: str) -> None:
        """Initialize or switch to a specific model."""
        try:
            model_config = {
                "model": model_type,
                "parameters": self.config.get("model_parameters", {})
            }
            
            model = OtherLLMModel(config=model_config)
            self.models[model_type] = model
            
            # Add to active conversation if one exists
            if self.conversation:
                self.conversation.add_model(model_type)
                
            logger.info(f"Initialized model: {model_type}")
            
        except Exception as e:
            logger.error(f"Failed to initialize model {model_type}: {e}")
            raise
    
    async def start_conversation(self) -> None:
        """Start a new conversation session."""
        self.conversation = ActiveConversation()
        # Add all current models to conversation
        for model_name in self.models:
            self.conversation.add_model(model_name)
    
    def _detect_addressed_model(self, message: str) -> Optional[str]:
        """Detect if a message is addressing a specific model."""
        message = message.lower()
        for model_name in self.models:
            if f"@{model_name}" in message:
                return model_name
        return None
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.conversation:
                await self.start_conversation()
                
            # Add user message to conversation
            await self.conversation.add_message(message, speaker="user")
            
            # Check if message is addressed to specific model
            model_name = self._detect_addressed_model(message)
            
            if model_name and model_name in self.models:
                # Get response from addressed model
                model = self.models[model_name]
                response = await model.generate_response(message)
                
                # Add model response to conversation
                await self.conversation.add_message(
                    content=response,
                    speaker=model_name
                )
                
                # Save conversation to scroll
                entry_id = await self.scroll.write_conversation(
                    content=self.conversation.format_conversation(),
                    metadata={
                        "active_models": list(self.conversation.active_models),
                        "start_time": self.conversation.start_time.isoformat(),
                    }
                )
                self.conversation.current_entry_id = entry_id
                
                return {
                    "response": response,
                    "model": model_name,
                    "entry_id": entry_id
                }
            
            return {
                "response": None,
                "model": None,
                "entry_id": self.conversation.current_entry_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise