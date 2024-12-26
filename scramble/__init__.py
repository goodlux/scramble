"""scRAMBLE - AI Enhanced Chat Interface"""
from .interface import RambleInterface
from .coordinator.coordinator import Coordinator
from .model.anthropic_llm_model import AnthropicLLMModel
from .magicscroll.magic_scroll import MagicScroll  # Full import path for clarity

__all__ = ['RambleInterface', 'Coordinator', 'AnthropicLLMModel', 'MagicScroll']
__version__ = "0.1.0"