"""Controller for message handling and processing."""
from typing import List, Dict, Any
from datetime import datetime
import dateparser

from ..core.context import Context

from uuid import uuid4
import numpy as np
from ..core.context import Context


class MessageController:
    """Handles message processing and model interactions."""
    
    def __init__(self, interface):
        """Initialize with reference to parent interface."""
        self.interface = interface
    
    async def handle_message(self, message: str) -> None:
        """Process a message and get model response."""
        try:
            # Get relevant contexts
            contexts = self.process_message(message)
            
            # Check for specific model request
            model = self.interface.model_coordinator.detect_model_from_message(message)
            
            # Send through coordinator
            response = await self.interface.model_coordinator.send_message(
                message=message,
                contexts=contexts,
                model=model
            )
            
            # Store context if we have a context manager
            if hasattr(self.interface, 'context_manager') and hasattr(self.interface, 'store'):
                self._store_context(message, response)
            
            # Display response
            await self.interface.display_output(response['response'])
            
        except Exception as e:
            await self.interface.display_error(f"Error processing message: {e}")
    

    def _store_context(self, message: str, response: Dict[str, Any]) -> None:
        """Store the message and response as context."""
        try:
            # Create metadata
            metadata = {
                'user_message': message,
                'assistant_response': response['response'],
                'model': response['model'],
                'timestamp': response['timestamp']
            }
            
            # Create full text content
            full_text = f"Human: {message}\n\nAssistant: {response['response']}"
            
            # Use compressor to create context
            context = self.interface.context_manager.compressor.compress(
                text=full_text,
                metadata=metadata
            )
            
            # Store it
            self.interface.store.add(context)
            
        except Exception as e:
            # Log error but don't stop execution
            print(f"Warning: Failed to store context: {e}")
            

    def process_message(self, message: str, use_all_contexts: bool = False) -> List[Context]:
        """Select relevant contexts for the message."""
        candidates = []

        # Check for temporal references
        if dateparser.parse(message):
            historical = self.interface.context_manager.find_contexts_by_timeframe(message)
            candidates.extend(historical)

        # Get contexts based on strategy
        if use_all_contexts:
            all_contexts = self.interface.store.list()
            similar = self.interface.context_manager.compressor.find_similar(
                message, 
                all_contexts, 
                top_k=10
            )
            candidates.extend([ctx for ctx, _, _ in similar])
        else:
            # Get recent contexts by default
            recent = self.interface.store.get_recent_contexts(hours=168)  # Last 7 days
            candidates.extend(recent)

            # Check for references to previous conversations
            if any(word in message.lower() for word in 
                  ['previous', 'before', 'earlier', 'last time', 'recall']):
                all_contexts = self.interface.store.list()
                similar = self.interface.context_manager.compressor.find_similar(
                    message, 
                    all_contexts, 
                    top_k=5
                )
                candidates.extend([ctx for ctx, _, _ in similar])

        # Let context manager make final selection
        return self.interface.context_manager.select_contexts(message, candidates)