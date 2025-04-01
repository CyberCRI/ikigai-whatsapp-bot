import asyncio
import json
import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple

import httpx
import websockets
from pywa_async import WhatsApp
from pywa_async.types import Button, CallbackButton, Message

from enums import Events, ResponseTypes
from schemas import ButtonData
from settings import settings

logger = logging.getLogger(__name__)


class BaseService(ABC):
    def __init__(self, whatsapp_client: WhatsApp):
        self.whatsapp_client = whatsapp_client

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

    async def _send_text(
        self, user_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        await self.whatsapp_client.send_message(user_id, text, buttons=buttons)

    async def _send_image(
        self, user_id: str, image: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        await self.whatsapp_client.send_image(user_id, image, buttons=buttons)

    async def send_message_to_user(self, response: Dict[str, Any]):
        receiver = response["receiver"]["platform_ids"][settings.IKIGAI_WEBSOCKET_PLATFORM_NAME]
        content = response.get("content", {}).get("message", None)
        buttons = response.get("buttons", [])
        if buttons or content:
            if not content:
                content = ""
            buttons = [
                Button(
                    title=button["label"],
                    callback_data=ButtonData(**button),
                )
                for button in buttons
            ]
            await self._send_text(receiver, content, buttons)

    async def send_image_to_user(self, response: Dict[str, Any]):
        receiver = response["receiver"]["platform_ids"][settings.IKIGAI_WEBSOCKET_PLATFORM_NAME]
        images = response.get("images", [])
        buttons = response.get("buttons", [])
        buttons = [
            Button(
                title=button["label"],
                callback_data=ButtonData(**button),
            )
            for button in buttons
        ]
        for image in images:
            # await self._send_image(receiver, image, buttons)
            await self._send_text(receiver, f"IMAGE : {image['file_name']}", buttons)

    async def add_role_to_user(self, response: Dict[str, Any]):
        pass

    async def remove_role_from_user(self, response: Dict[str, Any]):
        pass

    async def start_typing(self, response: Dict[str, Any]):
        pass

    async def stop_typing(self, response: Dict[str, Any]):
        pass

    async def handle_response(self, response: Dict[str, Any]):
        response = json.loads(response)
        action = response["action"]
        content = response["content"]
        match action:
            case ResponseTypes.MESSAGE.value:
                await self.send_message_to_user(content)
            case ResponseTypes.IMAGES.value:
                await self.send_image_to_user(content)
            case ResponseTypes.ADD_ROLE.value:
                await self.add_role_to_user(content)
            case ResponseTypes.REMOVE_ROLE.value:
                await self.remove_role_from_user(content)
            case ResponseTypes.START_TYPING.value:
                await self.start_typing(content)
            case ResponseTypes.STOP_TYPING.value:
                await self.stop_typing(content)


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
        whatsapp_client: WhatsApp,
        base_url: str = settings.IKIGAI_API_URL,
        token: str = settings.IKGAI_API_TOKEN,
        verify_ssl: bool = settings.HTTPX_CLIENT_VERIFY_SSL,
        timeout: int = settings.HTTPX_CLIENT_DEFAULT_TIMEOUT,
    ):
        """Initialize the APIClient."""
        headers = {"Content-type": "application/json", "Authorization": f"Bearer {token}"}
        self.session = httpx.AsyncClient(headers=headers, verify=verify_ssl, timeout=timeout)
        self.base_url = base_url
        super().__init__(whatsapp_client)

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
        self.websocket_url = websocket_url
        self.platform_name = platform_name
        self.connection_timeout = connection_timeout
        self.connections: Dict[str, websockets.connect] = {}
        super().__init__(whatsapp_client)

    async def get_or_create_connection(self, user_id: str) -> Tuple[websockets.connect, bool]:
        if user_id not in self.connections:
            connection = await websockets.connect(
                f"{self.websocket_url}/websocket/platform/{self.platform_name}/user/{user_id}",
                close_timeout=self.connection_timeout,
            )
            self.connections[user_id] = connection
            asyncio.create_task(self.listen_to_connection(connection, user_id))
            return connection, True
        return self.connections[user_id], False

    async def on_error(self, connection: websockets.connect, user_id: str, error: Exception):
        self.connections.pop(user_id, None)
        raise error

    async def on_close(self, connection: websockets.connect, user_id: str):
        logger.info(f"Closed websocket connection for user {user_id}")
        self.connections.pop(user_id, None)

    async def on_open(self, connection: websockets.connect, user_id: str):
        logger.info(f"Opened websocket connection for user {user_id}")

    async def post_message_to_server(self, message: Message, is_retry: bool = False):
        try:
            connection, _ = await self.get_or_create_connection(message.from_user.wa_id)
            json_message = json.dumps(self.serialize_message(message))
            await connection.send(json_message)
        except websockets.exceptions.ConnectionClosed as e:
            if is_retry:
                raise e
            self.connections.pop(message.from_user.wa_id, None)
            await self.post_message_to_server(message, is_retry=True)

    async def post_button_click_to_server(
        self, button_data: CallbackButton[ButtonData], is_retry: bool = False
    ):
        try:
            connection, _ = await self.get_or_create_connection(button_data.from_user.wa_id)
            json_message = json.dumps(self.serialize_button_click(button_data))
            await connection.send(json_message)
        except websockets.exceptions.ConnectionClosed as e:
            if is_retry:
                raise e
            self.connections.pop(button_data.from_user.wa_id, None)
            await self.post_button_click_to_server(button_data, is_retry=True)

    async def listen_to_connection(self, connection: websockets.connect, user_id: str):
        try:
            await self.on_open(connection, user_id)
            async for response in connection:
                await self.handle_response(response)
        except websockets.ConnectionClosed:
            await self.on_close(connection, user_id)
        except Exception as e:
            await self.on_error(connection, user_id, e)
        await self.on_close(connection, user_id)
