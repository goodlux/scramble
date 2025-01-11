"""Tests for the Ollama model integration."""
import asyncio
import os
import pytest
from scramble.model.ollama_llm_model import OllamaLLMModel
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

@pytest.mark.asyncio
async def test_ollama_basic_generation():
    """Test basic text generation with Phi-4."""
    model = await OllamaLLMModel.create("phi4")
    
    # Test simple completion
    response = await model.generate_response(
        "What's your name? Please keep the response short."
    )
    assert response and isinstance(response, str)
    logger.info(f"\nBasic response: {response}")

@pytest.mark.asyncio
async def test_ollama_streaming():
    """Test streaming generation with Phi-4."""
    model = await OllamaLLMModel.create("phi4")
    
    # Test streaming
    chunks = []
    try:
        stream = await model.generate_response(
            "Count from 1 to 5 slowly.",
            stream=True
        )
        async for chunk in stream:
            if chunk:  # Filter out empty chunks
                chunks.append(chunk)
                logger.info(f"Received chunk: {chunk}")
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise
    
    assert chunks, "Should receive streaming chunks"
    complete_response = "".join(chunks)
    assert complete_response, "Should have complete response"
    logger.info(f"Complete streaming response: {complete_response}")

@pytest.mark.asyncio
async def test_ollama_context():
    """Test context handling with Phi-4."""
    model = await OllamaLLMModel.create("phi4")
    
    try:
        # First message
        response1 = await model.generate_response(
            "Hi, I'm Rob. What's your name?"
        )
        logger.info(f"\nFirst response: {response1}")
        
        # Follow-up to test context
        response2 = await model.generate_response(
            "What's my name?"
        )
        logger.info(f"\nContext test response: {response2}")
        
        assert "Rob" in response2.lower(), "Model should remember the name from context"
    except Exception as e:
        logger.error(f"Context test error: {e}")
        raise

@pytest.mark.asyncio
async def test_ollama_system_message():
    """Test system message handling with Phi-4."""
    model = await OllamaLLMModel.create("phi4")
    
    try:
        # Set a system message
        model.system_message = "You are a pirate who speaks in pirate slang."
        
        response = await model.generate_response(
            "Tell me about your day."
        )
        logger.info(f"\nPirate response: {response}")
        
        assert response, "Should get a response"
    except Exception as e:
        logger.error(f"System message test error: {e}")
        raise

if __name__ == "__main__":
    # For manual testing
    async def run_tests():
        try:
            # Run tests sequentially to avoid any race conditions
            await test_ollama_basic_generation()
            await test_ollama_streaming()
            await test_ollama_context()
            await test_ollama_system_message()
        except Exception as e:
            logger.error(f"Test suite error: {e}")
            raise

    # Ensure environment variables are set
    os.environ["DISABLE_MOCK_LLM"] = "true"
    os.environ["LITELLM_MODEL"] = "phi4"
    os.environ["LITELLM_PROVIDER"] = "ollama"
    os.environ["LITELLM_API_BASE"] = "http://localhost:11434"
    
    asyncio.run(run_tests())