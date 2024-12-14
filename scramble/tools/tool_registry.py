from typing import Dict, Any, Literal, Optional
from .base import LocalTool, MCPTool

class ToolRegistry:
    """Registry for all types of tools."""
    
    def __init__(self):
        self.local_tools: Dict[str, LocalTool] = {}
        self.server_tools: Dict[str, MCPTool] = {}
        self.dynamic_tools: Dict[str, LocalTool] = {}  # Model-created tools
    
    async def register_local(self, tool: LocalTool) -> None:
        """Register built-in local tool."""
        self.local_tools[tool.name] = tool
    
    async def register_server(self, tool: MCPTool, server_url: str) -> None:
        """Register MCP server tool."""
        self.server_tools[tool.name] = tool
        
    async def register_dynamic(self, 
        name: str, 
        code: str,
        description: str,
        tool_type: Literal["ui", "code", "view"] = "code"
    ) -> None:
        """Let models register their own tools."""
        # Safely compile and create tool from model-provided code
        # This would need careful sandboxing!
        
    async def discover_servers(self, urls: List[str]) -> None:
        """Find and register available MCP servers."""
        for url in urls:
            try:
                tools = await self._get_server_tools(url)
                for tool in tools:
                    await self.register_server(tool, url)
            except Exception as e:
                logger.error(f"Failed to discover tools at {url}: {e}")

    async def run_tool(self, 
        name: str, 
        tool_type: Literal["local", "server", "dynamic"],
        **kwargs
    ) -> Dict[str, Any]:
        """Run any registered tool."""
        tools = {
            "local": self.local_tools,
            "server": self.server_tools,
            "dynamic": self.dynamic_tools
        }[tool_type]
        
        if name not in tools:
            raise ValueError(f"Unknown {tool_type} tool: {name}")
            
        return await tools[name].run(**kwargs)