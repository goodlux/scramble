"""Coordinates all model interactions through LLMHarness."""
from typing import Dict, Any, Optional, List
from datetime import datetime

from llmharness import LLMHarness
from ..core.context import Context

class ModelCoordinator:
    """Coordinates model interactions and maintains model state."""
    
    def __init__(self):
        """Initialize the coordinator with LLMHarness."""
        self.harness = LLMHarness()
        self._default_model = "claude-opus"  # Config name from models.yaml
    
    async def send_message(
        self, 
        message: str,
        contexts: Optional[List[Context]] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message to appropriate model."""
        try:
            # Use specified model or detect from message
            model_id = model or self._detect_model(message)
            
            # Build message format that liteLLM expects
            messages = [
                {"role": "user", "content": message}
            ]
            
            if contexts:
                # Add context as system message
                system_message = self._build_system_message(contexts)
                messages.insert(0, {"role": "system", "content": system_message})
            
            # Get response through harness
            response = await self.harness.complete(
                model=model_id,
                prompt=messages
            )
            
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            else:
                content = str(response)
            
            return {
                'response': content,
                'model': model_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Model coordinator error: {str(e)}")

    def detect_model_from_message(self, message: str) -> str:
        """Public method for detecting which model to use based on message content."""
        return self._detect_model(message)
    
    def _detect_model(self, message: str) -> str:
        """Internal model detection implementation."""
        message = message.lower()
        if "claude" in message:
            return "claude-opus"
        elif "gpt" in message:
            return "custom-model"  # The GPT-4 config from models.yaml
        return self._default_model
    
    def _build_system_message(self, contexts: List[Context]) -> str:
        """Build system message from contexts."""
        if not contexts:
            return "You are a helpful AI assistant."

        # Build context information
        context_parts = []
        for ctx in contexts:
            timestamp = ctx.created_at.strftime("%Y-%m-%d %H:%M")
            if 'user_message' in ctx.metadata and 'assistant_response' in ctx.metadata:
                context_parts.append(
                    f"[{timestamp}]\n"
                    f"User: {ctx.metadata['user_message']}\n"
                    f"Assistant: {ctx.metadata['assistant_response']}"
                )

        context_text = "\n\n".join(context_parts)
        
        return (
            "You are a helpful AI assistant. Here are relevant excerpts from our "
            f"previous conversations:\n\n{context_text}\n\n"
            "Please reference these previous discussions when relevant."
        )