import asyncio
import json
import logging
import httpx
import websocket
import websockets
import threading
from typing import Any, Dict, Tuple
from pywa_async import WhatsApp
from pywa_async.types import Message

from data_types import ButtonData
from settings import settings

logger = logging.getLogger(__name__)


class IkigaiClient:
    @classmethod
    def serialize_message(cls, message: Message) -> Dict[str, Any]:
        return {
            "id": 999999999,  # message.id
            "content": message.text,
            "author": {
                "id": 5000,  # message.from_user.wa_id,
                "username": message.from_user.name,
                "discriminator": "0",
                "avatar": {"url": ""},
            },
            "channel": {
                "id": 5000,  # message.from_user.wa_id,
                "name": message.from_user.wa_id,
                "type": 1,
                "guild": None,
                "used_for": None,
            },
            "created_at": str(message.timestamp.isoformat()),
            "edited_at": None,
        }
    
    @classmethod
    def serialize_interaction(cls, callback_data: ButtonData) -> Dict[str, Any]:
        return {
            "user_id": callback_data.user_id,
            "button_id": callback_data.button_id,
        }


class IkigaiAPIClient(IkigaiClient):
    """
    Client for interacting with the Ikigai API.

    Args:
        base_url (str): The base URL of the Ikigai API.
        token (str): The API token for the Ikigai API.
        verify_ssl (bool): Whether to verify SSL certificates.
        timeout (int): The timeout for requests.
    """

    def __init__(
        self,
        base_url: str = settings.IKIGAI_API_URL,
        token: str = settings.IKGAI_API_TOKEN,
        verify_ssl: bool = settings.HTTPX_CLIENT_VERIFY_SSL,
        timeout: int = settings.HTTPX_CLIENT_DEFAULT_TIMEOUT,
    ):
        """Initialize the IkigaiAPIClient."""
        headers = {"Content-type": "application/json", "Authorization": f"Bearer {token}"}
        self.session = httpx.AsyncClient(headers=headers, verify=verify_ssl, timeout=timeout)
        self.base_url = base_url

    async def _request(self, method: str, path: str, **kwargs):
        """Make a request to the API and handle response errors."""
        response = await self.session.request(method, f"{self.base_url}/{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    async def get(self, path: str, **kwargs):
        """Make a GET request to the API."""
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, payload: Dict[str, Any], **kwargs):
        """Make a POST request to the API."""
        return await self._request("POST", path, json=payload, **kwargs)

    async def put(self, path: str, payload: Dict[str, Any], **kwargs):
        """Make a PUT request to the API."""
        return await self._request("PUT", path, json=payload, **kwargs)

    async def patch(self, path: str, payload: Dict[str, Any], **kwargs):
        """Make a PATCH request to the API."""
        return await self._request("PATCH", path, json=payload, **kwargs)

    async def delete(self, path: str, **kwargs):
        """Make a DELETE request to the API."""
        return await self._request("DELETE", path, **kwargs)

    async def post_message(self, message: Message) -> httpx.Response:
        """
        Format and post a WhatsappMessage object to the API.

        Args:
            message (WhatsappMessage): The message to post.

        Returns:
            dict: The response from the API.
        """
        return await self.post("message", payload=self.serialize_message(message))
    
    async def post_interaction(self, callback_data: ButtonData) -> httpx.Response:
        """
        Format and post a ButtonData object to the API.

        Args:
            callback_data (ButtonData): The data to post.

        Returns:
            dict: The response from the API.
        """
        return await self.post(
            "interaction", payload=self.serialize_interaction(callback_data)
        )


class AsyncIkigaiWebSocketClient(IkigaiClient):

    def __init__(self, whatsapp_client: WhatsApp, websocket_url: str = settings.IKIGAI_WEBSOCKET_URL):
        self.whatsapp_client = whatsapp_client
        self.websocket_url = f"{websocket_url}/websocket"
        self.connections: Dict[str, websockets.connect] = {}

    async def get_or_create_connection(self, user_id: str) -> Tuple[websockets.connect, bool]:
        logger.error(f"DEBUG SAM : get_or_create_connection: {self.connections=}")
        if user_id not in self.connections:
            connection = await websockets.connect(self.websocket_url)
            self.connections[user_id] = connection
            asyncio.create_task(self.listen_to_connection(connection, user_id))
            return connection, True
        return self.connections[user_id], False
    
    async def on_message(self, connection: websockets.connect, message: str):
        logger.error(f"DEBUG SAM : on_message: {self.connections=}")
        message = json.loads(message)
        message_text = message.get("message", "")
        message_to = message.get("to")
        logger.error(f"Received message: {message_text}")
        await self.whatsapp_client.send_message(message_to, message_text)

    async def on_error(self, connection: websockets.connect, user_id: str, error: str):
        logger.error(f"DEBUG SAM : on_error: {self.connections=}")
        logger.error(f"Socket connection error: {error}")
        self.connections.pop(user_id, None)

    async def on_close(self, connection: websockets.connect, user_id: str):
        logger.error(f"DEBUG SAM : on_close: {self.connections=}")
        self.connections.pop(user_id, None)
        logger.error(f"Closed socket connection for user: {user_id}")

    async def on_open(self, connection: websockets.connect):
        logger.error(f"DEBUG SAM : on_open: {self.connections=}")
        logger.error("Opened socket connection")

    async def send_message(self, message: Message):
        logger.error(f"DEBUG SAM : send_message: {self.connections=}")
        logger.error("Sending message: %s", message)
        connection, _ = await self.get_or_create_connection(message.from_user.wa_id)
        json_message = json.dumps(self.serialize_message(message))
        await connection.send(json_message)

    async def listen_to_connection(self, connection: websockets.connect, user_id: str):
        try:
            await self.on_open(connection)
            async for message in connection:
                await self.on_message(connection, message)
        except websockets.ConnectionClosed as e:
            await self.on_close(connection, user_id)
        except Exception as e:
            await self.on_error(connection, user_id, str(e))
        await self.on_close(connection, user_id)
