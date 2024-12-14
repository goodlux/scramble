from typing import Dict, Any, Optional
from .types import MCPCommand, MCPResponse
from ..tools import ToolInterface

class MCPHandler:
    """Handles MCP (Managed Chat Protocol) interactions."""
    
    def __init__(self, tool_interface: ToolInterface):
        self.tool_interface = tool_interface
        
    async def handle_command(self, command: MCPCommand) -> MCPResponse:
        """Handle an MCP command."""
        if command.type == "tool_call":
            return await self.handle_tool_call(command)
        elif command.type == "context_update":
            return await self.handle_context_update(command)
        elif command.type == "system_request":
            return await self.handle_system_request(command)
        
        return MCPResponse(
            success=False,
            error="Unknown command type"
        )
    
    async def handle_tool_call(self, command: MCPCommand) -> MCPResponse:
        """Handle a tool being called through MCP."""
        try:
            result = await self.tool_interface.handle_tool_call(
                command.tool,
                **command.args
            )
            return MCPResponse(
                success=True,
                data=result
            )
        except Exception as e:
            return MCPResponse(
                success=False,
                error=str(e)
            )