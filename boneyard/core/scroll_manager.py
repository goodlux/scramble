from typing import Optional
from .scroll import Scroll, ScrollEntry
from llmharness import LLMHarness

class ScrollManager:
    """Manages the scroll and model interactions."""
    
    def __init__(self):
        self.scroll = Scroll()
        self.harness = LLMHarness()
        
    async def process_message(self, message: str) -> ScrollEntry:
        """Process a user message and get AI response."""
        # Add user message to scroll
        await self.scroll.add_entry(message)
        
        # Parse which model to use
        model = self._detect_model(message)
        
        # Get response from appropriate model
        response = await self.harness.generate(
            message,
            model=model,
            context=self._get_relevant_context()
        )
        
        # Add response to scroll
        return await self.scroll.add_entry(
            content=response.content,
            model=model,
            metadata={
                "usage": response.usage,
                "context_used": response.context_info
            }
        )
    
    def _detect_model(self, message: str) -> str:
        """Detect which model to use based on message."""
        message = message.lower()
        if "claude" in message:
            return "claude-3-opus"
        elif "gpt-4" in message:
            return "gpt-4"
        # ... add more model detection
        return "claude-3-opus"  # default