"""Anthropic Claude model implementation with temporal context handling."""
from typing import Dict, Any, AsyncGenerator, List, cast, Optional, Union
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ModelParam
import logging
from datetime import datetime
from .llm_model_base import LLMModelBase, Message, Role

logger = logging.getLogger(__name__)

class AnthropicLLMModel(LLMModelBase):
    """Implementation for Anthropic Claude models using official SDK."""
    
    # Additional class attributes specific to Anthropic
    client: Optional[AsyncAnthropic]

    def __init__(self):
        """Initialize the Anthropic model."""
        super().__init__()
        self.client = None
        self.max_context_length = 128_000  # Claude 3 context window

    async def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        if "api_key" not in self.config:
            raise ValueError("API key not found in config")
            
        self.client = AsyncAnthropic(
            api_key=self.config["api_key"]
        )

    async def generate_response(self, prompt: str, **params: Any) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using the model with temporal context handling."""
        if not self.client or not self.model_id:
            raise RuntimeError("Model not initialized")

        try:
            # Parse and inject temporal context
            enhanced_prompt = await self._inject_temporal_context(prompt)
            
            # Format the messages with context buffer
            messages = self._format_messages_with_context(enhanced_prompt)
            
            response = await self.client.messages.create(
                model=cast(ModelParam, self.model_id),
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            )
            
            # Extract response content
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                response_text = getattr(first_block, 'text', '')
                
                # Add response to context buffer with temporal metadata
                self._add_to_context(
                    role="assistant",
                    content=response_text,
                    metadata={
                        "model": self.model_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return response_text
            return ""
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def _format_messages_with_context(self, prompt: str) -> List[MessageParam]:
        """Format messages for the Anthropic API with context."""
        formatted_messages: List[MessageParam] = []
        
        # Add system message if present
        if self.system_message:
            formatted_messages.append(self._create_anthropic_message(
                "system",
                self.system_message
            ))
        
        # Add context buffer messages
        for msg in self.context_buffer:
            # Format temporal references if present
            content = msg["content"]
            if "temporal_references" in msg["metadata"]:
                refs = msg["metadata"]["temporal_references"]
                if refs:
                    content = self._format_temporal_context(content, refs)
            
            formatted_messages.append(self._create_anthropic_message(
                msg["role"],
                content
            ))
        
        # Add current prompt
        formatted_messages.append(self._create_anthropic_message(
            "user",
            prompt
        ))
        
        return formatted_messages

    def _format_temporal_context(self, content: str, temporal_refs: List[Dict[str, Any]]) -> str:
        """Format content with temporal reference annotations."""
        formatted_content = content
        
        # Add temporal context notes if needed
        if temporal_refs:
            temporal_context = "\nTemporal Context:\n"
            for ref in temporal_refs:
                temporal_context += f"- {ref['reference']}: {ref['timestamp']}\n"
            formatted_content = temporal_context + "\n" + formatted_content
            
        return formatted_content

    def _create_anthropic_message(self, role: Role, content: str) -> MessageParam:
        """Create a message in Anthropic's format."""
        return cast(MessageParam, {
            "role": role,
            "content": content
        })

    async def _generate_stream(
        self,
        prompt: str,
        **params: Any
    ) -> AsyncGenerator[str, None]:
        """Stream completion using Anthropic client with temporal context."""
        if not self.client or not self.model_name:
            raise RuntimeError("Model not properly initialized")

        try:
            # Inject temporal context
            enhanced_prompt = await self._inject_temporal_context(prompt)
            
            # Format messages with context
            messages = self._format_messages_with_context(enhanced_prompt)

            async with self.client.messages.stream(
                model=cast(ModelParam, self.model_name),
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            ) as stream:
                accumulated_response = ""
                
                async for chunk in stream:
                    if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                            text = getattr(chunk.delta, 'text', '')
                            if text:
                                accumulated_response += text
                                yield str(text)
                
                # After streaming completes, add to context buffer
                if accumulated_response:
                    self._add_to_context(
                        role="assistant",
                        content=accumulated_response,
                        metadata={
                            "model": self.model_name,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about model capabilities."""
        if not self.model_name:
            raise RuntimeError("Model not initialized")
            
        model_name = self.model_name
        return {
            "name": model_name,
            "provider": "Anthropic",
            "capabilities": [
                "chat",
                "code",
                "analysis",
                "creative",
                "math",
                "reasoning",
                "temporal_context"  # Added new capability
            ],
            "max_tokens": 4096 if (
                "opus" in model_name or 
                "sonnet" in model_name
            ) else 1024,
            "supports_system_message": True,
            "supports_functions": True,
            "supports_vision": (
                "opus" in model_name or 
                "sonnet" in model_name
            ),
            "supports_temporal_context": True  # Added new flag
        }