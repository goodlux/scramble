"""
FIPA ACL integration for the Scramble Coordinator system.

This module integrates the FIPA ACL standard into the existing Coordinator
architecture, allowing for standardized communication between different models
while maintaining backward compatibility.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import uuid
from datetime import datetime
import json
import logging

from scramble.magicscroll.digital_trinity.fipa_acl import FIPAACLMessage, FIPAACLDatabase
from scramble.magicscroll.digital_trinity.message_adapter import MessageAdapter
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

class FIPACoordinatorBridge:
    """Bridge between Coordinator and FIPA ACL messaging system."""
    
    def __init__(self):
        """Initialize the FIPA bridge."""
        self.db = FIPAACLDatabase()
        self.active_conversation_id: Optional[str] = None
        
    def start_new_conversation(self, title: Optional[str] = None) -> str:
        """
        Start a new FIPA ACL conversation.
        
        Args:
            title: Optional title for the conversation
            
        Returns:
            The conversation ID
        """
        try:
            self.active_conversation_id = self.db.create_conversation(title)
            logger.info(f"Started new FIPA conversation with ID: {self.active_conversation_id}")
            
            # Create system message marking the start of conversation
            system_msg = FIPAACLMessage(
                performative="INFORM",
                sender="system",
                content="Conversation started",
                conversation_id=self.active_conversation_id
            )
            self.db.save_message(system_msg)
            
            return self.active_conversation_id
        except Exception as e:
            logger.error(f"Error starting FIPA conversation: {e}")
            # Fall back to UUID if database fails
            self.active_conversation_id = str(uuid.uuid4())
            return self.active_conversation_id
    
    def add_message(
        self, 
        content: str,
        sender: str,
        recipient: Optional[str] = None,
        message_type: str = "user",  # "user", "model", "system"
        metadata: Optional[Dict[str, Any]] = None
    ) -> FIPAACLMessage:
        """
        Add a message to the active conversation.
        
        Args:
            content: Message content
            sender: Sender ID
            recipient: Optional recipient ID
            message_type: Type of message (user, model, system)
            metadata: Optional additional metadata
            
        Returns:
            The created FIPA ACL message
        """
        # Ensure we have an active conversation
        if not self.active_conversation_id:
            self.start_new_conversation()
        
        # Map message type to performative
        performative_map = {
            "user": "REQUEST",
            "model": "INFORM",
            "system": "INFORM"
        }
        performative = performative_map.get(message_type, "INFORM")
        
        # Create FIPA message
        message = FIPAACLMessage(
            performative=performative,
            sender=sender,
            receiver=recipient,
            content=content,
            conversation_id=self.active_conversation_id
        )
        
        # Add metadata
        if metadata:
            message.metadata.update(metadata)
        
        # Save to database
        try:
            self.db.save_message(message)
            logger.info(f"Added FIPA message from {sender} to conversation {self.active_conversation_id}")
        except Exception as e:
            logger.error(f"Error saving FIPA message: {e}")
        
        return message
    
    def get_conversation_history(self, conversation_id: Optional[str] = None) -> List[FIPAACLMessage]:
        """
        Get the message history for a conversation.
        
        Args:
            conversation_id: Optional conversation ID (uses active conversation if None)
            
        Returns:
            List of messages in the conversation
        """
        conv_id = conversation_id or self.active_conversation_id
        if not conv_id:
            logger.warning("No active conversation ID, returning empty history")
            return []
        
        try:
            return self.db.get_conversation_messages(conv_id)
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def convert_to_model_format(
        self, 
        messages: List[FIPAACLMessage], 
        model_type: str
    ) -> List[Dict[str, Any]]:
        """
        Convert FIPA messages to a model-specific format.
        
        Args:
            messages: List of FIPA ACL messages
            model_type: The model type (openai, anthropic)
            
        Returns:
            List of messages in the model's format
        """
        converted = []
        
        for msg in messages:
            if model_type == "openai":
                converted.append(MessageAdapter.fipa_to_openai(msg))
            elif model_type == "anthropic":
                converted.append(MessageAdapter.fipa_to_anthropic(msg))
            # Add other model types as needed
            else:
                # Default to OpenAI format
                converted.append(MessageAdapter.fipa_to_openai(msg))
        
        return converted
    
    def convert_from_model_response(
        self,
        response: Union[str, Dict[str, Any]],
        model_type: str,
        model_name: str,
        user_query_message: Optional[FIPAACLMessage] = None
    ) -> FIPAACLMessage:
        """
        Convert a model response to a FIPA message.
        
        Args:
            response: The model's response (string or dict)
            model_type: The model type (openai, anthropic)
            model_name: The name of the model
            user_query_message: The original user query message (for in-reply-to)
            
        Returns:
            FIPA ACL message
        """
        # Ensure we have an active conversation
        if not self.active_conversation_id:
            self.start_new_conversation()
        
        # Handle string responses
        if isinstance(response, str):
            msg = FIPAACLMessage(
                performative="INFORM",
                sender=model_name,
                receiver=user_query_message.sender if user_query_message else None,
                content=response,
                conversation_id=self.active_conversation_id
            )
            
            # Set in-reply-to if available
            if user_query_message:
                msg.in_reply_to = user_query_message.id
            
            # Save to database
            try:
                self.db.save_message(msg)
            except Exception as e:
                logger.error(f"Error saving model response to FIPA: {e}")
            
            return msg
        
        # Handle dictionary responses (model-specific formats)
        try:
            if model_type == "openai":
                msg = MessageAdapter.openai_to_fipa(
                    response,
                    conversation_id=self.active_conversation_id,
                    sender=model_name
                )
            elif model_type == "anthropic":
                msg = MessageAdapter.anthropic_to_fipa(
                    response,
                    conversation_id=self.active_conversation_id,
                    sender=model_name
                )
            # Add other model types as needed
            else:
                # Default handling
                msg = FIPAACLMessage(
                    performative="INFORM",
                    sender=model_name,
                    content=str(response),
                    conversation_id=self.active_conversation_id
                )
            
            # Set in-reply-to if available
            if user_query_message:
                msg.in_reply_to = user_query_message.id
            
            # Save to database
            try:
                self.db.save_message(msg)
            except Exception as e:
                logger.error(f"Error saving model response to FIPA: {e}")
            
            return msg
        except Exception as e:
            logger.error(f"Error converting model response to FIPA: {e}")
            # Fallback to simple string representation
            return FIPAACLMessage(
                performative="INFORM",
                sender=model_name,
                content=str(response),
                conversation_id=self.active_conversation_id
            )
    
    def register_model_agent(
        self,
        model_name: str,
        model_type: str,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a model as an agent in the FIPA system.
        
        Args:
            model_name: Name of the model
            model_type: Type of model (openai, anthropic, etc.)
            capabilities: Optional capabilities dictionary
            
        Returns:
            Agent ID
        """
        try:
            agent_id = self.db.register_agent(
                name=model_name,
                agent_type=model_type,
                capabilities=capabilities,
                agent_id=model_name  # Use model name as agent ID for simplicity
            )
            logger.info(f"Registered model {model_name} as FIPA agent with ID: {agent_id}")
            return agent_id
        except Exception as e:
            logger.error(f"Error registering model agent: {e}")
            return model_name
    
    def close(self):
        """Close the database connection."""
        try:
            self.db.close()
        except Exception as e:
            logger.error(f"Error closing FIPA database: {e}")
