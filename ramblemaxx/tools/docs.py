"""Document viewer control tool."""
from . import LocalTool
from typing import Dict, Any, Literal, Optional

class DocumentViewerTool(LocalTool):
    """Tool for controlling the document viewer panel."""
    
    name = "doc_viewer"
    description = "Display and manage documents in the side panel"
    
    async def run(
        self,
        action: Literal["show", "clear", "scroll"],
        content: Optional[str] = None,
        doc_type: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """Control document viewer."""
        return {
            "action": f"doc_{action}",
            "content": content,
            "metadata": {
                "tool": self.name,
                "doc_type": doc_type
            }
        }