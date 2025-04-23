"""Ollama-specific implementation for local LLM models."""
from typing import Dict, Any, AsyncGenerator, Union, Optional, List, TypedDict
import logging
from ollama import AsyncClient
from .llm_model_base import LLMModelBase, Message

logger = logging.getLogger(__name__)

class OllamaModelOptions(TypedDict, total=False):
    """Type definition for Ollama model options."""
    temperature: float
    top_p: float
    top_k: int
    num_predict: int
    mirostat: int
    mirostat_eta: float
    mirostat_tau: float
    stop: List[str]
    seed: int
    num_thread: int
    repeat_last_n: int
    repeat_penalty: float
    tfs_z: float
    num_gpu: int
    num_ctx: int

class OllamaLLMModel(LLMModelBase):
    """Implementation for Ollama-based local LLM models."""
    
    def __init__(self):
        """Basic initialization."""
        super().__init__()
        self.client: Optional[AsyncClient] = None
        self.base_url: str = "http://localhost:11434"
        
    async def _initialize_client(self) -> None:
        """Initialize Ollama client with configuration."""
        # Check if we're in simulation mode
        import os
        simulation_mode = os.environ.get('SIMULATE_MODELS', '0') == '1'
        
        if simulation_mode:
            logger.info(f"Simulation mode: Not connecting to Ollama for {self.model_name}")
            self.client = "SIMULATED"  # Just set a non-None value
            self.system_message = self.config.get("system_prompt", "")
            return
            
        try:
            # Get base_url from provider config if available
            provider_config = self.config.get("provider_config", {})
            self.base_url = provider_config.get("base_url", self.base_url)
            
            # Initialize the async client
            self.client = AsyncClient(host=self.base_url)
            
            # Set system prompt from config
            self.system_message = self.config.get("system_prompt")
            if self.system_message:
                logger.info(f"Initialized {self.model_name} with custom system prompt")
            
            logger.info(f"Successfully initialized Ollama client for {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {str(e)}")
            raise

    def _prepare_chat_messages(self) -> List[Dict[str, str]]:
        """Convert message history to Ollama-compatible chat format."""
        messages: List[Dict[str, str]] = []
        
        # Add system message if present
        if self.system_message:
            messages.append({
                "role": "system",
                "content": self.system_message
            })
        
        # Add conversation history
        for msg in self.context_buffer:
            messages.append({
                "role": "assistant" if msg["role"] == "assistant" else "user",
                "content": msg["content"]
            })
        
        return messages

    def _get_model_options(self, additional_options: Dict[str, Any] = None) -> OllamaModelOptions:
        """Get model options from config and additional options."""
        # Start with default options from config
        options: OllamaModelOptions = {
            "temperature": float(self.config.get("parameters", {}).get("temperature", 0.7)),
            "top_p": float(self.config.get("parameters", {}).get("top_p", 0.9)),
            "num_ctx": int(self.config.get("parameters", {}).get("max_tokens", 2048))
        }
        
        # Add any additional options
        if additional_options:
            options.update(additional_options)
            
        return options

    async def generate_response(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs: Any
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate a response using Ollama's API."""
        if not self.client:
            raise RuntimeError("Ollama client not initialized")
            
        try:
            # Add prompt to context
            self._add_to_context("user", prompt)

            # Prepare messages and options
            messages = self._prepare_chat_messages()
            options = self._get_model_options(kwargs)
            
            # Prepare request parameters
            params = {
                "model": self.model_id,
                "messages": messages,
                "stream": stream,
                "options": options
            }
            
            logger.debug(f"Generating response with parameters: {params}")
            
            if stream:
                return self._generate_stream(params)
            else:
                return await self._generate_completion(params)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            if stream:
                return self._empty_generator()
            return ""

    async def _generate_completion(self, params: Dict[str, Any]) -> str:
        """Generate a complete response."""
        # Check if we're in simulation mode
        import os
        simulation_mode = os.environ.get('SIMULATE_MODELS', '0') == '1'
        
        if simulation_mode:
            # Generate a simple simulated response
            prompt = params.get("messages", [])[-1].get("content", "") if params.get("messages") else ""
            simulated_response = f"[Simulated {self.model_name} Response] Echo: {prompt[:50]}..."
            logger.info(f"Simulation mode: Generated response for {self.model_name}")
            
            # Add to context buffer for conversation continuity
            self._add_to_context("assistant", simulated_response)
            return simulated_response
            
        try:
            if not self.client:
                raise RuntimeError("Ollama client not initialized")

            response = await self.client.chat(**params)
            if response and response.message:
                response_text = response.message["content"]
                logger.debug(f"Generated response: {response_text[:100]}...")  # Log first 100 chars
                # Add to context buffer for conversation continuity
                self._add_to_context("assistant", response_text)
                return response_text
            return ""
            
        except Exception as e:
            logger.error(f"Error in completion generation: {str(e)}")
            return ""
    
    async def _generate_stream(self, params: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        # Check if we're in simulation mode
        import os
        simulation_mode = os.environ.get('SIMULATE_MODELS', '0') == '1'
        
        if simulation_mode:
            # Generate a simple simulated streaming response
            prompt = params.get("messages", [])[-1].get("content", "") if params.get("messages") else ""
            simulated_response = f"[Simulated {self.model_name} Response] Echo: {prompt[:50]}..."
            
            # Split into chunks to simulate streaming
            chunks = [simulated_response[i:i+5] for i in range(0, len(simulated_response), 5)]
            
            # Add to context buffer
            self._add_to_context("assistant", simulated_response)
            
            # Yield chunks with small delays
            import asyncio
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.1)  # Simulate typing delay
            return
            
        if not self.client:
            raise RuntimeError("Ollama client not initialized")

        full_response = ""
        try:
            async for chunk in await self.client.chat(**params):
                if chunk and chunk.message and chunk.message.get("content"):
                    content = chunk.message["content"]
                    full_response += content
                    yield content
                    
            # Add complete response to context
            if full_response:
                self._add_to_context("assistant", full_response)
                    
        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}")
    
    async def _empty_generator(self) -> AsyncGenerator[str, None]:
        """Create an empty generator for error cases."""
        if False:  # This will never yield
            yield ""
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        options = self._get_model_options()
        return {
            "model_name": self.model_name,
            "model_id": self.model_id,
            "provider": "ollama",
            "max_context_length": options["num_ctx"],
            "supports_streaming": True,
            "supports_tools": False,  # Will be updated when tool support is added
            "supported_options": [
                "temperature", "top_p", "top_k", "num_predict", 
                "mirostat", "mirostat_eta", "mirostat_tau",
                "stop", "seed", "num_thread", "repeat_last_n",
                "repeat_penalty", "tfs_z", "num_gpu", "num_ctx"
            ]
        }