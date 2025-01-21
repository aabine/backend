from typing import Dict, Any
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.room_participants: Dict[str, set] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a client to the WebSocket."""
        await websocket.accept()
        self.active_connections[str(client_id)] = websocket

    def disconnect(self, client_id: str):
        """Disconnect a client from the WebSocket."""
        if str(client_id) in self.active_connections:
            del self.active_connections[str(client_id)]
        
        # Remove client from all rooms
        for room in self.room_participants.values():
            room.discard(str(client_id))

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client."""
        if str(client_id) in self.active_connections:
            websocket = self.active_connections[str(client_id)]
            await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections.values():
            await connection.send_json(message)

    def join_room(self, room: str, client_id: str):
        """Add a client to a room."""
        if room not in self.room_participants:
            self.room_participants[room] = set()
        self.room_participants[room].add(str(client_id))

    def leave_room(self, room: str, client_id: str):
        """Remove a client from a room."""
        if room in self.room_participants:
            self.room_participants[room].discard(str(client_id))
            if not self.room_participants[room]:
                del self.room_participants[room]

    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """Broadcast a message to all clients in a room."""
        if room in self.room_participants:
            for client_id in self.room_participants[room]:
                await self.send_personal_message(message, client_id) 