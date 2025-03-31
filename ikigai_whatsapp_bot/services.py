import asyncio
import json
import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple

import httpx
import websockets
from pywa_async import WhatsApp
from pywa_async.types import Button, CallbackButton, Message

from enums import Events, MessageType
from schemas import ButtonData
from settings import settings

logger = logging.getLogger(__name__)


class BaseService(ABC):
    @classmethod
    def serialize_message(cls, message: Message) -> Dict[str, Any]:
        return {
            "action": Events.MESSAGE.value,
            "content": {
                "content": message.text,
                "author": {
                    "platform_id": {
                        "id": message.from_user.wa_id,
                    },
                    "username": message.from_user.name,
                    "guild": None,
                },
                "channel": {
                    "platform_id": {
                        "id": message.from_user.wa_id,
                    },
                    "name": message.from_user.name,
                    "type": "dm",
                    "guild": None,
                },
            },
        }

    @classmethod
    def serialize_button_click(cls, callback_data: CallbackButton[ButtonData]) -> Dict[str, Any]:
        return {
            "action": Events.BUTTON_CLICK.value,
            "content": {
                "id": callback_data.data.id,
                "custom_id": callback_data.data.custom_id,
                "user": {
                    "platform_id": {
                        "id": callback_data.from_user.wa_id,
                    },
                    "username": callback_data.from_user.name,
                    "guild": None,
                },
                "channel": {
                    "platform_id": {
                        "id": callback_data.from_user.wa_id,
                    },
                    "name": callback_data.from_user.name,
                    "type": "dm",
                    "guild": None,
                },
            },
        }


class APIService(BaseService):
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
        """Initialize the APIClient."""
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

    async def post_button(self, callback_data: Button) -> httpx.Response:
        """
        Format and post a Button object to the API.

        Args:
            callback_data (Button): The data to post.

        Returns:
            dict: The response from the API.
        """
        return await self.post("Button", payload=self.serialize_button_click(callback_data))


class WebSocketService(BaseService):

    def __init__(
        self,
        whatsapp_client: WhatsApp,
        websocket_url: str = settings.IKIGAI_WEBSOCKET_URL,
        platform_name: str = settings.IKIGAI_WEBSOCKET_PLATFORM_NAME,
        connection_timeout: int = 10,
    ):
        self.whatsapp_client = whatsapp_client
        self.websocket_url = websocket_url
        self.platform_name = platform_name
        self.connection_timeout = connection_timeout
        self.connection: Optional[websockets.connect] = None

    async def get_or_create_connection(self) -> Tuple[websockets.connect, bool]:
        if self.connection is None:
            connection = await websockets.connect(
                f"{self.websocket_url}/websocket/platform/{self.platform_name}",
                close_timeout=self.connection_timeout,
            )
            self.connection = connection
            asyncio.create_task(self.listen_to_connection(connection))
            return connection, True
        return self.connection, False

    async def _send_text(
        self, user_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        await self.whatsapp_client.send_message(user_id, text, buttons=buttons)

    async def _send_image(
        self, user_id: str, image: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        await self.whatsapp_client.send_image(user_id, image, buttons=buttons)

    async def on_message(self, connection: websockets.connect, message: Dict[str, Any]):
        message = json.loads(message)
        logger.error(f"Received message: {message}")
        result = {
            "id": 1,
            "receiver": {"id": 1, "username": "Samer", "platform_ids": {"whatsapp": "33601090133"}},
            "channel": {"id": 1, "name": "Samer", "platform_ids": {"whatsapp": "33601090133"}},
            "content": "Welcome ${user_mention}! I'm Spark, your Ikigai guide. **Click the button** and then find me in your **private messages**!",
            "files": [],
            "buttons": [
                {
                    "id": 1,
                    "style": 3,
                    "label": "✨ Click to start ✨",
                    "clicked": False,
                    "remove_after_click": True,
                }
            ],
        }
        receiver = message["receiver"]["platform_ids"][settings.IKIGAI_WEBSOCKET_PLATFORM_NAME]
        content = message.get("content", "")
        buttons = message.get("buttons", [])
        buttons = [
            Button(
                title=button["label"],
                callback_data=ButtonData(**button),
            )
            for button in buttons
        ]
        for file in message.get("files", []):
            await self._send_image(receiver, content, buttons)
        await self._send_text(receiver, content, buttons)

    async def on_error(self, connection: websockets.connect, error: str):
        logger.error(f"Error on websocket connection {str(connection)}: {error}")
        self.connections = None

    async def on_close(self, connection: websockets.connect):
        logger.info(f"Closed websocket connection {str(connection)}")
        self.connections = None

    async def on_open(self, connection: websockets.connect):
        logger.info(f"Opened websocket connection {str(connection)}")

    async def send_message(self, message: Message, is_retry: bool = False):
        try:
            connection, _ = await self.get_or_create_connection()
            json_message = json.dumps(self.serialize_message(message))
            await connection.send(json_message)
        except websockets.exceptions.ConnectionClosed as e:
            if is_retry:
                raise e
            self.connection = None
            await self.send_message(message, is_retry=True)

    async def send_button_click(
        self, button_data: CallbackButton[ButtonData], is_retry: bool = False
    ):
        try:
            connection, _ = await self.get_or_create_connection()
            json_message = json.dumps(self.serialize_button_click(button_data))
            await connection.send(json_message)
        except websockets.exceptions.ConnectionClosed as e:
            if is_retry:
                raise e
            self.connection = None
            await self.send_button_click(button_data, is_retry=True)

    async def listen_to_connection(self, connection: websockets.connect):
        try:
            await self.on_open(connection)
            async for message in connection:
                await self.on_message(connection, message)
        except websockets.ConnectionClosed as e:
            await self.on_close(connection)
        except Exception as e:
            await self.on_error(connection, str(e))
        await self.on_close(connection)
