# interface/tool_controller.py
"""Controller for tool registration and execution."""
from typing import Dict, Any, Optional, List
from ..tool.tool_base import ScrollTool, LocalTool
from ..tool.tool_registry import ToolRegistry

class ToolController:
    """Handles tool registration and execution."""
    
    def __init__(self, interface):
        """Initialize with reference to parent interface."""
        self.interface = interface
        self.tool_registry = ToolRegistry()
        self._interface_tools: Dict[str, LocalTool] = {}
    
    async def register_tool(self, tool: ScrollTool) -> None:
        """Register a tool with this interface."""
        if isinstance(tool, LocalTool):
            self._interface_tools[tool.name] = tool
            await self.tool_registry.register_local(tool)
            # Update interface capabilities
            self.interface.capabilities['available_tools'] = \
                self.interface.capabilities.get('available_tools', {})
            self.interface.capabilities['available_tools'][tool.name] = {
                'description': tool.description
            }
    
    async def handle_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Handle a tool being called."""
        try:
            if tool_name in self._interface_tools:
                return await self.tool_registry.run_tool(
                    name=tool_name,
                    tool_type="local",
                    **kwargs
                )
            else:
                raise ValueError(f"Tool {tool_name} not available in this interface")
        except Exception as e:
            await self.interface.display_error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def get_available_tools(self) -> List[str]:
        """Get list of available tools for this interface."""
        return list(self._interface_tools.keys())
    
    async def describe_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get description of a specific tool."""
        if tool_name in self._interface_tools:
            tool = self._interface_tools[tool_name]
            return {
                'name': tool.name,
                'description': tool.description,
                'type': 'local'
            }
        return None