"""Enhanced Coordinator with FIPA ACL integration."""
from typing import Dict, List, Any, Optional, Tuple, Union
import asyncio
from datetime import datetime
import re

from scramble.utils.logging import get_logger
from scramble.utils.context_debugger import context_debugger
from .coordinator import Coordinator
from .enhanced_conversation import EnhancedConversation
from .fipa_integration import FIPACoordinatorBridge
from scramble.magicscroll.digital_trinity.fipa_acl import FIPAACLMessage

logger = get_logger(__name__)

class EnhancedCoordinator(Coordinator):
    """Enhanced Coordinator with FIPA ACL support for multi-model communication."""
    
    def __init__(self):
        """Initialize the enhanced coordination system."""
        super().__init__()
        self.fipa_bridge = FIPACoordinatorBridge()
        self.use_fipa = True  # Flag to enable/disable FIPA features
    
    @classmethod
    async def create(cls) -> 'EnhancedCoordinator':
        """Create and initialize enhanced coordinator."""
        coordinator = cls()
        
        # Initialize base coordinator
        await super(EnhancedCoordinator, coordinator).create()
        
        # Additional initialization for enhanced features
        logger.info("Initializing enhanced coordinator with FIPA support")
        
        # Start FIPA conversation
        conversation_id = coordinator.fipa_bridge.start_new_conversation()
        logger.info(f"Started FIPA conversation with ID: {conversation_id}")
        
        return coordinator
    
    async def start_conversation(self) -> None:
        """Start a new conversation session with FIPA support."""
        # Create enhanced conversation instead of regular
        self.active_conversation = EnhancedConversation()
        
        # Reset FIPA conversation
        self.fipa_bridge.start_new_conversation()
        
        # Add models to conversation
        for model_name in self.active_models:
            self.active_conversation.add_model(model_name)
            
            # Register model as FIPA agent
            model = self.active_models[model_name]
            model_type = model.__class__.__name__.lower()
            if "anthropic" in model_type:
                model_type = "anthropic"
            elif "openai" in model_type:
                model_type = "openai"
            elif "ollama" in model_type:
                model_type = "ollama"
                
            self.fipa_bridge.register_model_agent(
                model_name=model_name,
                model_type=model_type
            )
        
        # Add system message for conversation start
        if self.active_conversation:  # Type guard
            # Standard message
            await self.active_conversation.add_message(
                content="Started new conversation session",
                speaker="system",
                recipient=None
            )
            
            # FIPA message
            start_msg = FIPAACLMessage(
                performative="INFORM",
                sender="system",
                content="Started new conversation session",
                conversation_id=self.fipa_bridge.active_conversation_id
            )
            
            if isinstance(self.active_conversation, EnhancedConversation):
                await self.active_conversation.add_fipa_message(start_msg)
            
            logger.info("New enhanced conversation session started")
    
    async def add_model_to_conversation(self, model_name: str) -> None:
        """Add a new model to the active set with FIPA registration."""
        # Use the standard implementation first
        await super().add_model_to_conversation(model_name)
        
        # Register model as FIPA agent
        if model_name in self.active_models:
            model = self.active_models[model_name]
            model_type = model.__class__.__name__.lower()
            if "anthropic" in model_type:
                model_type = "anthropic"
            elif "openai" in model_type:
                model_type = "openai"
            elif "ollama" in model_type:
                model_type = "ollama"
                
            self.fipa_bridge.register_model_agent(
                model_name=model_name,
                model_type=model_type
            )
            
            # Add model added message to FIPA conversation
            if self.use_fipa:
                msg = FIPAACLMessage(
                    performative="INFORM",
                    sender="system",
                    content=f"{model_name} was added to the conversation",
                    conversation_id=self.fipa_bridge.active_conversation_id
                )
                
                self.fipa_bridge.db.save_message(msg)
                
                # Add to enhanced conversation if available
                if isinstance(self.active_conversation, EnhancedConversation):
                    await self.active_conversation.add_fipa_message(msg)
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message with FIPA enhancements."""
        # Handle debug commands
        if message.startswith('/debug'):
            return await self._handle_debug_command(message)
            
        try:
            # Initialize conversation if needed
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
            
            # Create a FIPA message for the user's input
            user_fipa_msg = None
            if self.use_fipa:
                user_fipa_msg = FIPAACLMessage(
                    performative="REQUEST",
                    sender="user",
                    receiver=mentioned_model or responding_model,
                    content=message,
                    conversation_id=self.fipa_bridge.active_conversation_id
                )
                
                # Save to FIPA database
                self.fipa_bridge.db.save_message(user_fipa_msg)
            
            # Add user message to conversation
            await self.active_conversation.add_message(
                message,
                speaker="user",
                recipient=mentioned_model
            )
            
            # Add FIPA message to enhanced conversation if available
            if user_fipa_msg and isinstance(self.active_conversation, EnhancedConversation):
                await self.active_conversation.add_fipa_message(user_fipa_msg)
            
            # Build context for the model
            context = await self._build_model_context(
                message=message,
                model_name=responding_model,
                mentioned_model=mentioned_model
            )
            
            # Get a reference to the model
            model = self.active_models[responding_model]
            
            # Add FIPA history to the context if this model supports it
            if self.use_fipa and hasattr(model, 'supports_fipa') and model.supports_fipa:
                # Get model type for format conversion
                model_type = model.__class__.__name__.lower()
                if "anthropic" in model_type:
                    model_type = "anthropic"
                elif "openai" in model_type or "oai" in model_type:
                    model_type = "openai"
                else:
                    model_type = "default"
                
                # Get history formatted for this model
                if isinstance(self.active_conversation, EnhancedConversation):
                    fipa_history = self.active_conversation.get_fipa_history(for_model=responding_model)
                else:
                    fipa_history = self.fipa_bridge.get_conversation_history()
                
                # Convert to model format
                model_messages = self.fipa_bridge.convert_to_model_format(fipa_history, model_type)
                
                # Add to model context
                logger.info(f"Adding FIPA history ({len(model_messages)} messages) to context for {responding_model}")
                # Pass the converted messages to the model
                model.set_message_history(model_messages)
            
            # Generate response
            response = await model.generate_response(context)
            
            # Process response
            response_text = await self._process_model_response(response)
            
            # Create FIPA message for the model's response
            model_fipa_msg = None
            if self.use_fipa:
                # Convert response to FIPA
                model_type = model.__class__.__name__.lower()
                if "anthropic" in model_type:
                    model_type = "anthropic"
                elif "openai" in model_type or "oai" in model_type:
                    model_type = "openai"
                else:
                    model_type = "default"
                
                model_fipa_msg = self.fipa_bridge.convert_from_model_response(
                    response=response_text,
                    model_type=model_type,
                    model_name=responding_model,
                    user_query_message=user_fipa_msg
                )
            
            # Add model response to conversation
            await self.active_conversation.add_message(
                content=response_text,
                speaker=responding_model,
                recipient="User"  # TODO: Replace with actual user ID
            )
            
            # Add FIPA message to enhanced conversation if available
            if model_fipa_msg and isinstance(self.active_conversation, EnhancedConversation):
                await self.active_conversation.add_fipa_message(model_fipa_msg)
            
            return {
                "response": response_text,
                "model": responding_model
            }
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    async def save_conversation_to_magicscroll(self) -> Optional[str]:
        """Save the current conversation to MagicScroll storage with FIPA data."""
        try:
            # Check for active conversation
            if not self.active_conversation:
                logger.warning("No active conversation to save")
                return None
                
            # Check for MagicScroll
            if not self.magicscroll:
                logger.warning("MagicScroll not available - conversation will not be saved")
                return None
            
            # Create conversation entry with enhanced data if available
            from scramble.magicscroll.ms_entry import MSConversation
            
            if isinstance(self.active_conversation, EnhancedConversation):
                # Use enhanced format with FIPA data
                content = self.active_conversation.format_conversation()
                metadata = {
                    "start_time": self.active_conversation.start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "has_fipa_data": True,
                    "fipa_conversation_id": self.fipa_bridge.active_conversation_id
                }
            else:
                # Use standard format
                content = self.active_conversation.format_conversation()
                metadata = {
                    "start_time": self.active_conversation.start_time.isoformat(),
                    "end_time": datetime.utcnow().isoformat()
                }
            
            conversation = MSConversation(
                content=content,
                metadata=metadata
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
    
    async def close(self) -> None:
        """Close connections."""
        # Close FIPA bridge
        if hasattr(self, 'fipa_bridge'):
            self.fipa_bridge.close()
            
        # Close base coordinator connections if any