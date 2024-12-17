"""Base class for Scramble's LLM models."""
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
from abc import ABC, abstractmethod
import logging
from datetime import datetime

from llmharness.llm_model import LLMModel as HarnessModel
from ..tool.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class LLMModelBase(HarnessModel, ABC):
    """Base class adding Scramble-specific features to LLMHarness models."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the model with Scramble features.
        
        Args:
            config: Model configuration
        """
        super().__init__()
        self.config = config or {}
        self.tool_registry = ToolRegistry()
        self.context_buffer: List[Dict[str, Any]] = []
        self.max_context_length = self.config.get("max_context_length", 4096)
    
    async def generate_response(
        self, 
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using the model.
        
        Args:
            prompt: The input prompt
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            The model's response
        """
        try:
            # Format prompt with context
            formatted_prompt = self._format_prompt_with_context(prompt)
            
            # Check for tool calls
            if self._contains_tool_call(formatted_prompt):
                return await self._handle_tool_call(formatted_prompt)
            
            # Generate response through harness
            response = await self.complete(
                harness=self.harness,
                prompt=formatted_prompt,
                stream=stream,
                **kwargs
            )
            
            # Update context buffer
            self._update_context_buffer(prompt, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _format_prompt_with_context(self, prompt: str) -> str:
        """Format the prompt with current context buffer."""
        context_str = "\n".join(
            f"{msg['role']}: {msg['content']}" 
            for msg in self.context_buffer[-5:]  # Last 5 messages for context
        )
        
        return f"""Previous conversation:
{context_str}

Current message:
User: {prompt}