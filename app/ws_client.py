import asyncio
import websockets
import json

class WebSocketClient:
    def __init__(self, api_host, api_base):
        self.api_host = api_host
        self.api_base = api_base
        self.client_id = None
        self.socket = None

    async def create_socket(self, is_reconnect=False):
        if self.socket:
            return

        existing_session = f"?clientId={self.client_id}" if self.client_id else ""
        uri = f"ws://{self.api_host}{self.api_base}{existing_session}"
        self.socket = await websockets.connect(uri)

    async def receive_message(self):
        try:
            message = await self.socket.recv()
            return message
        except websockets.ConnectionClosed:
            print("Connection closed")
            await self.socket.close()
            return None
        except Exception as e:
            print(f"Exception: {e}")
            await self.socket.close()
            return None