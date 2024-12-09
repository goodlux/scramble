from fastapi import WebSocket
from scramble.core.api import API
from scramble.core.context import Context
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, Context] = {}
        self.api = API()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = Context()

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def process_message(self, websocket: WebSocket, message: str):
        context = self.active_connections[websocket]
        response = await self.api.process_message(message, context)
        await websocket.send_text(json.dumps({
            "sender": "noumena",
            "content": response
        }))
