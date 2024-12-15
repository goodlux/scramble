from scramble.tools.base import LocalTool
from typing import Dict, Any, Literal, Optional

class CodePanelTool(LocalTool):
    """Tool for managing the code panel."""
    
    name = "code_panel"
    description = "Manage code panel in RambleMAXX"
    
    async def run(
        self,
        action: Literal["write", "execute", "clear"],
        content: Optional[str] = None,
        language: str = "python",
        entry = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Manage code panel content and execution."""
        return {
            "action": f"code_{action}",
            "content": content,
            "metadata": {
                "tool": self.name,
                "code_action": action,
                "language": language
            }
        }