from dataclasses import dataclass
from typing import Dict, Optional, List
import asyncio
import logging
from .client import ToolClient

logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    """Configuration for a tool server"""
    command: Optional[dict] = None  # Command to start server
    settings: Optional[dict] = None # Server-specific settings

@dataclass
class ServerCommand:
    """Command to start a server"""
    path: str
    args: List[str]
    env: Optional[Dict[str, str]] = None

class ToolServer:
    """Represents a single tool server"""

    def __init__(self, server_id: str, config: ServerConfig):
        self.id = server_id
        self.config = config
        self.client: Optional[ToolClient] = None
        self._process = None

    async def start(self):
        """Start the tool server"""
        if self.config.command:
            cmd = ServerCommand(**self.config.command)
            # Start server process
            self._process = await asyncio.create_subprocess_exec(
                cmd.path,
                *cmd.args,
                env=cmd.env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        # Connect client
        self.client = ToolClient(f"ws://localhost:8765/{self.id}")  # URL would come from config
        await self.client.connect()

    async def stop(self):
        """Stop the tool server"""
        if self.client:
            await self.client.disconnect()
            self.client = None

        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None

class ToolServerManager:
    """Manages multiple tool servers"""

    def __init__(self):
        self.servers: Dict[str, ToolServer] = {}

    async def start_server(self, server_id: str, config: ServerConfig):
        """Start a new tool server"""
        if server_id in self.servers:
            await self.stop_server(server_id)

        server = ToolServer(server_id, config)
        try:
            await server.start()
            self.servers[server_id] = server
            logger.info(f"Started server {server_id}")
        except Exception as e:
            logger.error(f"Failed to start server {server_id}: {e}")
            await server.stop()
            raise

    async def stop_server(self, server_id: str):
        """Stop a tool server"""
        if server := self.servers.pop(server_id, None):
            await server.stop()
            logger.info(f"Stopped server {server_id}")

    async def restart_server(self, server_id: str):
        """Restart a tool server"""
        if server := self.servers.get(server_id):
            config = server.config
            await self.stop_server(server_id)
            await self.start_server(server_id, config)

    def get_server(self, server_id: str) -> Optional[ToolServer]:
        """Get a server by ID"""
        return self.servers.get(server_id)

    async def stop_all(self):
        """Stop all servers"""
        for server_id in list(self.servers.keys()):
            await self.stop_server(server_id)
