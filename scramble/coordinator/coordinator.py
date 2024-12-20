"""Core coordination system for Scramble."""
from typing import Optional, Dict, Any, List
import logging
import yaml
from pathlib import Path

from .active_conversation import ActiveConversation
from ..model.other_llm_model import OtherLLMModel
from ..magicscroll.magic_scroll import MagicScroll

logger = logging.getLogger(__name__)

class Coordinator:
    """Coordinator for model and scroll system."""
    
    def __init__(self):
        """Initialize the coordination system."""
        self.scroll: Optional[MagicScroll] = None
        self.active_models: Dict[str, OtherLLMModel] = {}
        self.conversation: Optional[ActiveConversation] = None
        
        # Load model configurations
        config_path = Path("llmharness/config/models.yaml")
        with open(config_path) as f:
            self.model_configs = yaml.safe_load(f)["models"]
    
    async def initialize(self) -> None:
        """Initialize the coordinator."""
        try:
            self.scroll = MagicScroll()            
            logger.info("Core systems initialized")
        except Exception as e:
            logger.error(f"Failed to initialize core systems: {e}")
            raise

    async def add_model(self, model_type: str) -> None:
        """Add a new model to the active set."""
        try:
            # Check if model exists in config
            if model_type not in self.model_configs:
                raise ValueError(f"Model {model_type} not found in configuration")

            model_config = {
                "model": model_type,
                "parameters": self.model_configs[model_type].get("parameters", {})
            }
            
            model = OtherLLMModel(config=model_config)
            self.active_models[model_type] = model
            
            # Add to active conversation if one exists
            if self.conversation:
                self.conversation.add_model(model_type)
                
            logger.info(f"Added model: {model_type}")
            
        except Exception as e:
            logger.error(f"Failed to add model {model_type}: {e}")
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
        # Add all current models to conversation
        for model_name in self.active_models:
            self.conversation.add_model(model_name)
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message through the conversation system."""
        try:
            if not self.conversation:
                await self.start_conversation()
                
            if not self.scroll:
                raise RuntimeError("MagicScroll not initialized")
                
            if not self.conversation:  # Double-check after start_conversation
                raise RuntimeError("Failed to initialize conversation")
                
            # Now we can safely use conversation methods
            await self.conversation.add_message(message, speaker="user")
            
            # For now, just use the first active model
            if not self.active_models:
                raise RuntimeError("No active models available")
            
            model_name = next(iter(self.active_models.keys()))
            model = self.active_models[model_name]
            
            # Get response from model
            response = await model.generate_response(message)
            
            # Handle both string and AsyncGenerator responses
            if isinstance(response, str):
                response_text = response
            else:
                # Collect streaming response
                response_chunks = []
                async for chunk in response:
                    response_chunks.append(chunk)
                response_text = "".join(response_chunks)
            
            # We know conversation is not None here
            await self.conversation.add_message(
                content=response_text,
                speaker=model_name
            )
            
            # Save conversation to scroll
            formatted_conv = self.conversation.format_conversation()
            metadata = ["conversation"]  # Match MagicScroll's expected List[str] type
            
            entry_id = await self.scroll.write_conversation(
                content=formatted_conv,
                metadata=metadata
            )
            
            # We know conversation is not None here
            self.conversation.current_entry_id = entry_id
            
            return {
                "response": response_text,
                "model": model_name,
                "entry_id": entry_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise