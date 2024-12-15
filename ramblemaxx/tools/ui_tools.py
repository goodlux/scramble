"""General UI control tools."""
from . import LocalTool
from typing import Dict, Any, Literal, Optional

class ModelSelectorTool(LocalTool):
    """Tool for managing model selection."""
    
    name = "model_select"
    description = "Switch between different language models"
    
    async def run(
        self,
        action: Literal["switch", "list"],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Control model selection."""
        return {
            "action": f"model_{action}",
            "content": model,
            "metadata": {
                "tool": self.name,
                "model": model
            }
        }

class ThemeSwitcherTool(LocalTool):
    """Tool for controlling UI themes."""
    
    name = "theme"
    description = "Control UI theme settings"
    
    async def run(
        self,
        action: Literal["switch", "list"],
        theme: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Control theme settings."""
        return {
            "action": f"theme_{action}",
            "content": theme,
            "metadata": {
                "tool": self.name,
                "theme": theme
            }
        }