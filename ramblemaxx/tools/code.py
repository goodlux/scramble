from scramble.core.tools import ScrollTool
from typing import Literal, Optional, Dict, Any

class CodePanelTool(ScrollTool):
    name = "code_panel"
    description = "Manage code panel in RambleMaxx"
    
    async def run(self,
        action: Literal["write", "execute", "clear"],
        content: Optional[str] = None,
        language: str = "python",
        **kwargs
    ) -> Dict[str, Any]:
        """Manage code panel content and execution."""