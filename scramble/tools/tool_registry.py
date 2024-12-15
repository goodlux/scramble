import logging
from typing import Dict, Any, Literal, Optional
from .tool_base import LocalTool, MCPTool, DynamicTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for all types of tools."""
    
    def __init__(self):
        self.local_tools: Dict[str, LocalTool] = {}
        self.server_tools: Dict[str, MCPTool] = {}
        self.dynamic_tools: Dict[str, DynamicTool] = {}
    
    async def register_local(self, tool: LocalTool) -> None:
        """Register built-in local tool."""
        self.local_tools[tool.name] = tool
    
    async def register_server(self, tool: MCPTool, server_url: str) -> None:
        """Register MCP server tool."""
        tool.server_url = server_url
        self.server_tools[tool.name] = tool
        
    async def register_dynamic(self, 
        name: str, 
        code: str,
        description: str,
        tool_type: Literal["ui", "code", "view"] = "code"
    ) -> None:
        """Let models register their own tools."""
        # Basic implementation to use all parameters
        tool = DynamicTool()
        tool.name = name
        tool.description = description
        tool.source_code = code
        tool.tool_type = tool_type
        self.dynamic_tools[name] = tool
        
    async def discover_servers(self, urls: list[str]) -> None:
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
        entry: Optional[Dict[str, Any]] = None,
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
            
        return await tools[name].run(entry=entry, **kwargs)

    async def _get_server_tools(self, url: str) -> list[MCPTool]:
        """Get available tools from MCP server."""
        # Basic implementation to satisfy return type
        return [MCPTool()]  # Return empty list until implemented