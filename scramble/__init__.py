"""scRAMBLE - AI Enhanced Chat Interface"""
from .interface import RambleInterface
from .coordinator.coordinator import Coordinator
from .model.anthropic_llm_model import AnthropicLLMModel
from .magicscroll.magic_scroll import MagicScroll
from .config import Config

__all__ = ['RambleInterface', 'Coordinator', 'AnthropicLLMModel', 'MagicScroll', 'Config']
__version__ = "0.1.0"