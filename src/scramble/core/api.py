from typing import Dict, List, Optional, Any
import anthropic
import logging
from datetime import datetime, timedelta
from .context import Context
from .compressor import SemanticCompressor

logger = logging.getLogger(__name__)

class AnthropicClient:
    """Handles interaction with Anthropic's API with semantic compression."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "claude-3-opus-20240229",
                 compressor: Optional[SemanticCompressor] = None):
        """Initialize the Anthropic client."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.compressor = compressor or SemanticCompressor()
        self.current_context: Optional[Context] = None
        
    def send_message(self, 
                     message: str, 
                     contexts: Optional[List[Context]] = None,
                     max_tokens: int = 1024,
                     temperature: float = 0.7) -> Dict[str, Any]:
        """Send a message to Claude with context management."""
        try:
            # Create message with current API format
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            # Extract response text 
            # The response.content[0] is a Content object that we need to convert to string
            response_text = str(response.content[0])
            
            # Compress and store the new context
            metadata = {
                'timestamp': datetime.utcnow().isoformat(),
                'model': self.model,
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