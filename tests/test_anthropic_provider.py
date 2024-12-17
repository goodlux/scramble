"""Tests for the Anthropic provider."""
import pytest
from unittest.mock import Mock, patch
import anthropic
from llmharness.providers.anthropic import AnthropicProvider, AnthropicResponse

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client fixture."""
    with patch('anthropic.Anthropic') as mock:
        # Create a mock response
        mock_message = Mock()
        mock_message.id = "test_id"
        mock_message.model = "claude-3-opus-20240229"
        mock_message.content = [Mock(text="Test response")]
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 20
        
        # Set up the mock client
        mock_client = mock.return_value
        mock_client.messages.create.return_value = mock_message
        
        yield mock_client

@pytest.mark.asyncio
async def test_anthropic_provider_complete(mock_anthropic_client):
    """Test the complete method."""
    provider = AnthropicProvider(api_key="test_key")
    
    messages = [{"role": "user", "content": "Hello"}]
    response = await provider.complete(
        messages=messages,
        model="claude-3-opus-20240229",
        max_tokens=100,
        temperature=0.7
    )
    
    # Check response format
    assert isinstance(response, AnthropicResponse)
    assert response.id == "test_id"
    assert response.model == "claude-3-opus-20240229"
    assert len(response.choices) == 1
    assert response.choices[0]["message"]["content"] == "Test response"
    assert response.usage["prompt_tokens"] == 10
    assert response.usage["completion_tokens"] == 20
    
    # Verify API call
    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-3-opus-20240229",
        messages=messages,
        max_tokens=100,
        temperature=0.7
    )

def test_anthropic_response_validation(mock_anthropic_client):
    """Test response validation."""
    provider = AnthropicProvider(api_key="test_key")
    
    # Test valid response
    assert provider.validate_response("This is a valid response")
    
    # Test invalid responses
    assert not provider.validate_response("")
    assert not provider.validate_response(None)
    assert not provider.validate_response("I apologize, but I cannot process that request")
    assert not provider.validate_response("ERROR: Something went wrong")