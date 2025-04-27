"""
Test script to verify the context handling in model implementations.

This script tests:
1. That the AnthropicLLMModel properly handles context with "PREVIOUS CONVERSATIONS REFERENCE:"
2. That the OllamaLLMModel properly handles context with "PREVIOUS CONVERSATIONS REFERENCE:"

Run with: python -m tests.test_context_handling
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scramble.model.anthropic_llm_model import AnthropicLLMModel
from scramble.model.ollama_llm_model import OllamaLLMModel
from scramble.model.llm_model_base import LLMModelBase


# Mock context with "PREVIOUS CONVERSATIONS REFERENCE:"
MOCK_CONTEXT = """PREVIOUS CONVERSATIONS REFERENCE:
Relevant previous conversations:

    [Conversation ID: conv-1] - 2025-04-25 14:30
    Topic: blimps
    User: Hey, what do you know about blimps?
    Granite to User: Blimps are lighter-than-air aircraft that rely on gas (usually helium) for lift. Unlike rigid airships like zeppelins, blimps have no internal framework and maintain their shape through internal pressure.
    ---

CURRENT MESSAGE:
Do you remember when we talked about blimps?"""


async def test_anthropic_model():
    """Test AnthropicLLMModel context handling."""
    print("Testing AnthropicLLMModel context handling...")
    
    # Create a mock class for testing
    class MockAnthropicLLMModel(AnthropicLLMModel):
        async def _initialize_client(self):
            self.client = "MOCK"
            self.model_id = "claude-3-opus-20240229"
        
        def _create_anthropic_message(self, role, content):
            return {"role": role, "content": content}
    
    model = MockAnthropicLLMModel()
    model.system_message = "You are an AI assistant."
    
    # Call the method we're testing
    messages = model._format_messages_with_context(MOCK_CONTEXT)
    
    # Check results
    print(f"Generated {len(messages)} messages")
    for i, msg in enumerate(messages):
        print(f"Message {i+1}:")
        print(f"  Role: {msg['role']}")
        print(f"  Content preview: {msg['content'][:50]}...")
    
    # Verify correct splitting
    system_contexts = [msg for msg in messages if msg['role'] == 'system' and 'Relevant previous conversations' in msg['content']]
    user_messages = [msg for msg in messages if msg['role'] == 'user' and 'Do you remember when we talked about blimps?' in msg['content']]
    
    if len(system_contexts) > 0 and len(user_messages) > 0:
        print("✅ Test passed - Context correctly parsed")
    else:
        print("❌ Test failed - Context not correctly parsed")
        if len(system_contexts) == 0:
            print("  No system message with context found")
        if len(user_messages) == 0:
            print("  No user message with actual query found")


async def test_ollama_model():
    """Test OllamaLLMModel context handling."""
    print("\nTesting OllamaLLMModel context handling...")
    
    # Create a mock class for testing
    class MockOllamaLLMModel(OllamaLLMModel):
        async def _initialize_client(self):
            self.client = "MOCK"
            self.model_id = "granite-sparse:2b"
    
    model = MockOllamaLLMModel()
    model.system_message = "You are an AI assistant."
    
    # Add context to buffer and test
    model._add_to_context("user", MOCK_CONTEXT)
    
    # Call the method we're testing
    messages = model._prepare_chat_messages()
    
    # Check results
    print(f"Generated {len(messages)} messages")
    for i, msg in enumerate(messages):
        print(f"Message {i+1}:")
        print(f"  Role: {msg['role']}")
        print(f"  Content preview: {msg['content'][:50]}...")
    
    # Verify correct splitting
    system_contexts = [msg for msg in messages if msg['role'] == 'system' and 'Relevant previous conversations' in msg['content']]
    user_messages = [msg for msg in messages if msg['role'] == 'user' and 'Do you remember when we talked about blimps?' in msg['content']]
    
    if len(system_contexts) > 0 and len(user_messages) > 0:
        print("✅ Test passed - Context correctly parsed")
    else:
        print("❌ Test failed - Context not correctly parsed")
        if len(system_contexts) == 0:
            print("  No system message with context found")
        if len(user_messages) == 0:
            print("  No user message with actual query found")


async def main():
    """Run all tests."""
    await test_anthropic_model()
    await test_ollama_model()


if __name__ == "__main__":
    asyncio.run(main())
