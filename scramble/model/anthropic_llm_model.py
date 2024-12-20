"""Anthropic Claude model implementation using official SDK."""
from typing import Dict, Any, AsyncGenerator, List, Literal, TypedDict, cast
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam
import logging
from .llm_model_base import LLMModelBase

logger = logging.getLogger(__name__)

# Type definitions
Role = Literal["user", "assistant"]

class APIMessage(TypedDict):
    """Type for API-compatible message format."""
    role: Role
    content: str

class AnthropicLLMModel(LLMModelBase):
    """Implementation for Anthropic Claude models using official SDK."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Anthropic model."""
        super().__init__(config)
        
        # Claude-specific context settings
        self.max_context_length = 128_000  # Claude 3 context window
        self.client: AsyncAnthropic | None = None

    async def initialize(self) -> None:
        """Initialize the Anthropic client."""
        if not self.validate_config():
            raise ValueError("Invalid configuration")
            
        self.client = AsyncAnthropic(
            api_key=self.config["api_key"]
        )

    def validate_config(self) -> bool:
        """Validate the configuration."""
        if not super().validate_config():
            return False
            
        if "api_key" not in self.config:
            logger.error("Anthropic API key required in config")
            return False
            
        # Validate model name format
        valid_prefixes = ["claude-3-", "claude-2"]
        if not any(self.model_name.startswith(prefix) for prefix in valid_prefixes):
            logger.error(f"Invalid model name format: {self.model_name}")
            return False
            
        return True

    def _create_message(self, role: Role, content: str) -> MessageParam:
        """Create a properly typed message for the Anthropic API."""
        return cast(MessageParam, {
            "role": role,
            "content": content
        })

    def _format_messages_for_anthropic(self) -> List[MessageParam]:
        """Convert context buffer to Anthropic message format."""
        messages: List[MessageParam] = []
        
        # Handle system message as a user message for Claude 3
        if self.system_message:
            messages.append(self._create_message(
                "user",
                f"System: {self.system_message}"
            ))
        
        for msg in self.context_buffer:
            # Only include messages with valid roles
            if msg["role"] not in ["user", "assistant"]:
                continue
                
            messages.append(self._create_message(
                cast(Role, msg["role"]),
                msg["content"]
            ))
            
        return messages

    async def _generate_completion(
        self,
        prompt: str,
        **params: Any
    ) -> str:
        """Generate completion using Anthropic client."""
        if not self.client:
            await self.initialize()
            if not self.client:
                raise RuntimeError("Failed to initialize client")

        try:
            # Format messages properly
            api_messages = params.get("messages", [])
            if not api_messages:
                api_messages = [self._create_message("user", prompt)]

            response = await self.client.messages.create(
                model=self.model_name,
                messages=api_messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7)
            )
            
            # Extract text from response
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
        if not self.client:
            await self.initialize()
            if not self.client:
                raise RuntimeError("Failed to initialize client")

        try:
            # Format messages properly
            api_messages = params.get("messages", [])
            if not api_messages:
                api_messages = [self._create_message("user", prompt)]

            stream = await self.client.messages.create(
                model=self.model_name,
                messages=api_messages,
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.7),
                stream=True
            )
            
            async for chunk in stream:
                # For streaming, we need to check the type and extract text safely
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
        return {
            "name": self.model_name,
            "provider": "Anthropic",
            "capabilities": [
                "chat",
                "code",
                "analysis",
                "creative",
                "math",
                "reasoning"
            ],
            "max_tokens": 4096 if "opus" in self.model_name or "sonnet" in self.model_name else 1024,
            "supports_system_message": True,
            "supports_functions": True,
            "supports_vision": "opus" in self.model_name or "sonnet" in self.model_name
        }