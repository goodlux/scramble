"""Anthropic Claude model implementation using official SDK."""
from typing import Dict, Any, AsyncGenerator, List, cast
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ModelParam
import logging
from .llm_model_base import LLMModelBase

logger = logging.getLogger(__name__)

class AnthropicLLMModel(LLMModelBase):
    """Implementation for Anthropic Claude models using official SDK."""
    
    def __init__(self):
        """Initialize the Anthropic model."""
        super().__init__()
        self.client: AsyncAnthropic | None = None
        self.max_context_length = 128_000  # Claude 3 context window

    async def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        self.client = AsyncAnthropic(
            api_key=self.config["api_key"]
        )

    async def generate_response(self, prompt: str, **params: Any) -> str:
        """Generate a response using the model."""
        if not self.client or not self.model_id:
            raise RuntimeError("Model not initialized")

        try:
            response = await self.client.messages.create(
                model=cast(ModelParam, self.model_id),  # Use model_id here
                messages=[{"role": "user", "content": prompt}],
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            )
            
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                return getattr(first_block, 'text', '')
            return ""
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def _create_anthropic_message(self, role: str, content: str) -> MessageParam:
        """Create a message in Anthropic's format."""
        return cast(MessageParam, {
            "role": role,
            "content": content
        })

    async def _generate_completion(
        self,
        prompt: str,
        **params: Any
    ) -> str:
        """Generate completion using Anthropic client."""
        if not self.client or not self.model_name:
            raise RuntimeError("Model not properly initialized. Use create() to initialize the model.")

        try:
            messages = params.get("messages", [])
            if not messages:
                messages = [self._create_anthropic_message("user", prompt)]

            response = await self.client.messages.create(
                model=cast(ModelParam, self.model_name),
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            )
            
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                return getattr(first_block, 'text', '')
            return ""
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    async def _generate_stream(
        self,
        prompt: str,
        **params: Any
    ) -> AsyncGenerator[str, None]:
        """Stream completion using Anthropic client."""
        if not self.client or not self.model_name:
            raise RuntimeError("Model not properly initialized. Use create() to initialize the model.")

        try:
            messages = params.get("messages", [])
            if not messages:
                messages = [self._create_anthropic_message("user", prompt)]

            async with self.client.messages.stream(
                model=cast(ModelParam, self.model_name),
                messages=messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            ) as stream:
                async for chunk in stream:
                    if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                        if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                            text = getattr(chunk.delta, 'text', '')
                            if text:
                                yield str(text)
                        
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
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
                "reasoning"
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
            )
        }