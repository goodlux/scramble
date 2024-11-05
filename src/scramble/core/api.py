from typing import Dict, List, Optional, Any, Union, Iterable
import anthropic

from anthropic.types import (
    Message, 
    TextBlock, 
    ToolUseBlock, 
    ContentBlock, 
    TextBlockParam,
    MessageParam
)

from anthropic._types import NotGiven, NOT_GIVEN

import logging
from datetime import datetime, timedelta
from .context import Context
from .compressor import SemanticCompressor

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Handles interaction with Anthropic's API with semantic compression and conversation persistence."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "claude-3-5-sonnet-20241022",
                 compressor: Optional[SemanticCompressor] = None,
                 max_context_messages: int = 10):
        """Initialize the Anthropic client."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.compressor = compressor or SemanticCompressor()
        self.max_context_messages = max_context_messages
        self.message_history: List[MessageParam] = []
        self.current_context: Optional[Context] = None
        
    def _build_messages_from_context(self, contexts: List[Context]) -> List[MessageParam]:
        """Convert contexts into a list of messages for the API."""
        messages: List[MessageParam] = []
        
        # Extract conversations from contexts
        for ctx in contexts:
            if 'user_message' in ctx.metadata and 'assistant_response' in ctx.metadata:
                messages.extend([
                    {
                        "role": "user",
                        "content": ctx.metadata['user_message']
                    },
                    {
                        "role": "assistant",
                        "content": ctx.metadata['assistant_response']
                    }
                ])
        
        # Add message history
        messages.extend(self.message_history)
        
        # Trim to most recent messages if needed
        if len(messages) > self.max_context_messages:
            messages = messages[-self.max_context_messages:]
            
        return messages
    
    def _build_system_message(self, contexts: List[Context]) -> str:
        """Build system message incorporating context themes and relevant information."""
        if not contexts:
            return "You are Claude, a helpful AI assistant."
        
        # Extract key chunks from contexts with timestamps
        context_parts = []
        for ctx in contexts:
            timestamp = ctx.created_at.strftime("%Y-%m-%d %H:%M")
            
            # Get the most relevant chunks
            for chunk in ctx.compressed_tokens[:3]:  # Limit to top 3 chunks per context
                if isinstance(chunk, dict):
                    speaker = chunk.get('speaker', '')
                    content = chunk.get('content', '')
                    if speaker and content:
                        context_parts.append(f"[{timestamp}] {speaker}: {content}")
                elif isinstance(chunk, str):
                    context_parts.append(f"[{timestamp}] {chunk}")

        context_text = "\n".join(context_parts)
        
        return f"""You are Claude, a helpful AI assistant. Here are relevant excerpts from our previous conversations, marked with timestamps:
                {context_text}
                Please feel free to reference these previous discussions by their timestamps when relevant. Otherwise, engage naturally in our current conversation."""
        
    def send_message(self, 
                     message: str, 
                     contexts: Optional[List[Context]] = None,
                     max_tokens: int = 1024,
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Send a message to Claude with conversation persistence."""
        try:
            # Get relevant contexts if none provided
            if contexts is None and self.current_context is not None:
                similar = self.compressor.find_similar(message, [self.current_context])
                contexts = [c for c, _, _ in similar] if similar else []
            
            # Build message history from contexts and current history
            messages = self._build_messages_from_context(contexts or [])
            
            # Add current message
            current_message: MessageParam = {
                "role": "user",
                "content": message
            }
            messages.append(current_message)
            
            # Create message with current API format
            response: Message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=self._build_system_message(contexts or []),
                messages=messages
            )
            
            # Extract response text from first content block
            content: ContentBlock = response.content[0]
            if isinstance(content, TextBlock):
                response_text = content.text
            elif isinstance(content, ToolUseBlock):
                response_text = f"Tool Use: {content.name}"
            else:
                response_text = str(content)
            
            # Update message history
            self.message_history.append(current_message)
            self.message_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Trim history if needed
            if len(self.message_history) > self.max_context_messages:
                self.message_history = self.message_history[-self.max_context_messages:]
            
            # Update context with metadata
            metadata = {
                'timestamp': datetime.utcnow().isoformat(),
                'referenced_contexts': [ctx.id for ctx in (contexts or [])],
                'model': self.model,
                'user_message': message,
                'assistant_response': response_text,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            }
            
            self.current_context = self.compressor.compress(
                f"Human: {message}\n\nAssistant: {response_text}",
                metadata=metadata
            )
            
            return {
                'response': response_text,
                'context': self.current_context,
                'used_contexts': contexts,
                'usage': metadata['usage']
            }
            
        except Exception as e:
            logger.error(f"Error in Anthropic API call: {e}")
            raise