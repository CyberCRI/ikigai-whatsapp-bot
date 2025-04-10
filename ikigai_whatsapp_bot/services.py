import asyncio
import json
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import httpx
import websockets
from pywa_async import filters as pywa_filters
from pywa_async import WhatsApp
from pywa_async.types import Button, CallbackButton, Message
from pywa_async.types.sent_message import SentMessage

from enums import ChannelTypes, Events, ResponseTypes
from schemas import (
    ButtonData,
    ButtonResponse,
    ImageResponse,
    MessageResponse,
    RoleResponse,
    TypingResponse,
)
from settings import settings

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Base class for services that interact with the Ikigai Server.

    To use it, create a service class that inherits from this class. When receiving a task from the
    server :
    - Send events to the server :
        first serialize the event using the `serialize_message` or `serialize_button_click` methods.
    - Handle responses from the server:
        Call the `add_response_to_queue` method with the user ID and the response content to handle
        the task. The service will automatically create a queue for the user if it doesn't exist and
        process the task in the background.

    Arguments:
        whatsapp_client (WhatsApp): The WhatsApp client instance.

    Attributes:
        whatsapp_client (WhatsApp): The WhatsApp client instance.
        user_queues (Dict[str, Queue]): A dictionary mapping user IDs to their message queues.
        user_tasks (Dict[str, Task]): A dictionary mapping user IDs to their processing tasks.
    """

    def __init__(self, whatsapp_client: WhatsApp):
        self.whatsapp_client = whatsapp_client
        self.user_queues: Dict[str, asyncio.Queue] = {}
        self.user_tasks: Dict[str, asyncio.Task] = {}

    async def _wait_for_message_to_be_sent(
        self, message: SentMessage, timeout: int = settings.QUEUE_TASK_TIMEOUT
    ):
        """Wait for the message to be sent to avoid out of order messages."""
        await message._client.listen(  # pylint: disable=W0212
            to=message.recipient,
            sent_to_phone_id=message.sender,
            filters=pywa_filters.update_id(message.id) & pywa_filters.sent,
            cancelers=None,
            timeout=timeout,
        )

    async def _create_buttons(self, buttons: List[ButtonResponse]) -> List[Button]:
        """Create buttons from the response."""
        return [
            Button(
                title=button.label[:20],
                callback_data=ButtonData(
                    id=button.id,
                    custom_id=button.custom_id,
                    style=button.style,
                    label=button.label,
                    clicked=button.clicked,
                    remove_after_click=button.remove_after_click,
                ),
            )
            for button in buttons
        ]

    async def _send_text(
        self, user_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        """Send a text message with optional buttons to a user."""
        if buttons and len(buttons) > 3:
            sent_message = await self.whatsapp_client.send_message(
                user_id, text, buttons=buttons[:3]
            )
            await self._wait_for_message_to_be_sent(sent_message)
            for i in range(3, len(buttons), 3):
                buttons_chunk = buttons[i : i + 3]
                await self._send_text(
                    user_id, settings.EMPTY_MESSAGE_CONTENT, buttons=buttons_chunk
                )
        else:
            sent_message = await self.whatsapp_client.send_message(user_id, text, buttons=buttons)
            await self._wait_for_message_to_be_sent(sent_message)

    async def _send_image(
        self,
        user_id: str,
        image: str,
        caption: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
    ):
        """Send an image with optional buttons to a user."""
        if buttons and len(buttons) > 3:
            sent_image = await self.whatsapp_client.send_image(
                user_id, image, caption, buttons=buttons[:3]
            )
            await self._wait_for_message_to_be_sent(sent_image)
            for i in range(3, len(buttons), 3):
                buttons_chunk = buttons[i : i + 3]
                await self._send_text(
                    user_id, settings.EMPTY_MESSAGE_CONTENT, buttons=buttons_chunk
                )
        else:
            sent_image = await self.whatsapp_client.send_image(
                user_id, image, caption, buttons=buttons
            )
            await self._wait_for_message_to_be_sent(sent_image)

    async def _send_sticker(self, user_id: str, sticker: str):
        """
        Send a sticker to a user.
        """
        sent_sticker = await self.whatsapp_client.send_sticker(user_id, sticker)
        await self._wait_for_message_to_be_sent(sent_sticker)

    async def _send_message_to_user(self, response: MessageResponse):
        user = response.user.platform_ids[settings.CLIENT_NAME]
        content = response.message or settings.EMPTY_MESSAGE_CONTENT
        if response.buttons or content:
            buttons = await self._create_buttons(response.buttons)
            await self._send_text(user, content, buttons)

    async def _send_image_to_user(self, response: ImageResponse):
        user = response.user.platform_ids[settings.CLIENT_NAME]
        image = response.image
        caption = response.caption
        buttons = await self._create_buttons(response.buttons)
        if image.endswith(".gif"):
            # Convert GIF to WEBP format and send it as a sticker
            image = str(image).rsplit(".", 1)[0] + ".webp"
            if buttons or caption:
                logger.warning(
                    "Stickers do not support buttons or captions, sending only the sticker."
                )
            await self._send_sticker(user, image)
        await self._send_image(user, image, caption, buttons)

    async def _add_role_to_user(self, response: Dict[str, Any]):
        pass

    async def _remove_role_from_user(self, response: Dict[str, Any]):
        pass

    async def _start_typing(self, response: Dict[str, Any]):
        pass

    async def _stop_typing(self, response: Dict[str, Any]):
        pass

    async def _handle_response(
        self, action: ResponseTypes, content: Dict[str, Any]
    ) -> ResponseTypes:
        match action:
            case ResponseTypes.MESSAGE.value:
                content = MessageResponse(**content)
                await self._send_message_to_user(content)
            case ResponseTypes.IMAGE.value:
                content = ImageResponse(**content)
                await self._send_image_to_user(content)
            case ResponseTypes.ADD_ROLE.value:
                content = RoleResponse(**content)
                await self._add_role_to_user(content)
            case ResponseTypes.REMOVE_ROLE.value:
                content = RoleResponse(**content)
                await self._remove_role_from_user(content)
            case ResponseTypes.START_TYPING.value:
                content = TypingResponse(**content)
                await self._start_typing(content)
            case ResponseTypes.STOP_TYPING.value:
                content = TypingResponse(**content)
                await self._stop_typing(content)
        return action

    def _get_or_create_queue(self, user_id: str) -> asyncio.Queue:
        """
        Get or create a queue for the specified user.
        """
        if user_id not in self.user_queues:
            self.user_queues[user_id] = asyncio.Queue()
            self.user_tasks[user_id] = asyncio.create_task(self._process_queue(user_id))
        return self.user_queues[user_id]

    def _close_queue(self, user_id: str):
        """
        Close the queue for the specified user.
        """
        logger.info("Closing queue for user %s", user_id)
        self.user_queues.pop(user_id, None)
        self.user_tasks.pop(user_id, None)

    async def _process_queue(self, user_id: str):
        """
        Process the message queue for a specific user.
        """
        queue = self.user_queues[user_id]
        while True:
            task = await queue.get()
            try:
                event = await self._handle_response(task["action"], task["content"])
                if event == ResponseTypes.STOP_PROCESS.value:
                    self._close_queue(user_id)
                    break
            except Exception:  # pylint: disable=W0718
                logger.error("Failed to process task %s for user %s", task["action"], user_id)
                logger.error(traceback.format_exc())
            finally:
                queue.task_done()

    async def add_response_to_queue(self, user_id: str, response: Dict[str, Any]):
        """
        Add a message to the user's queue.
        """
        queue = self._get_or_create_queue(user_id)
        await queue.put(response)

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
                    "type": ChannelTypes.DM.value,
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
                    "type": ChannelTypes.DM.value,
                    "guild": None,
                },
            },
        }

    @abstractmethod
    async def post_message_to_server(self, message: Message):
        """
        Serialize an incoming pywa_async.types.Message object and send it to the server.
        """
        raise NotImplementedError

    @abstractmethod
    async def post_button_click_to_server(self, button_data: CallbackButton[ButtonData]):
        """
        Serialize an incoming pywa_async.types.CallbackButton object and send it to the server.
        """
        raise NotImplementedError


class APIService(BaseService):
    """
    Client for interacting with the Ikigai API.

    Arguments:
        whatsapp_client (WhatsApp): The WhatsApp client instance.
        platform_name (str): The name of the client (e.g., "whatsapp")
        api_url (str): The base URL of the Ikigai API endpoint.
        token (str): The API token for authentication.
        verify_ssl (bool): Whether to verify SSL certificates.
        timeout (int): The timeout for HTTP requests.
    """

    def __init__(
        self,
        whatsapp_client: WhatsApp,
        platform_name: str = settings.CLIENT_NAME,
        api_url: str = settings.IKIGAI_API_URL,
        token: str = settings.IKIGAI_API_KEY,
        verify_ssl: bool = settings.HTTPX_CLIENT_VERIFY_SSL,
        timeout: int = settings.HTTPX_CLIENT_DEFAULT_TIMEOUT,
    ):
        """Initialize the APIClient."""
        super().__init__(whatsapp_client)
        self.platform_name = platform_name
        self.api_url = api_url
        headers = {"Content-type": "application/json", settings.IKIGAI_API_KEY_HEADER_NAME: token}
        self.session = httpx.AsyncClient(headers=headers, verify=verify_ssl, timeout=timeout)

    async def _request(self, method: str, path: str, **kwargs):
        """Make a request to the API and handle response errors."""
        response = await self.session.request(method, f"{self.api_url}{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, payload: Dict[str, Any], **kwargs):
        """Make a POST request to the API."""
        return await self._request("POST", path, json=payload, **kwargs)

    async def post_message_to_server(self, message: Message):
        """
        Serialize an incoming message event and send it to the server via API.
        """
        payload = self.serialize_message(message)
        response = await self.post(f"/api/platform/{self.platform_name}", payload)
        for task in response:
            await self.add_response_to_queue(message.from_user.wa_id, task)

    async def post_button_click_to_server(self, button_data: CallbackButton[ButtonData]):
        """
        Serialize an incoming button click event and send it to the server via API.
        """
        payload = self.serialize_button_click(button_data)
        response = await self.post(f"/api/platform/{self.platform_name}", payload)
        for task in response:
            await self.add_response_to_queue(button_data.from_user.wa_id, task)


class WebSocketService(BaseService):
    """
    Client for interacting with the Ikigai WebSocket endpoint.

    This class manages WebSocket connections for each user and handles sending and receiving
    messages. It extends the BaseService class that handles all of the instructions received from
    the server.

    Arguments:
        whatsapp_client (WhatsApp): The WhatsApp client instance.
        platform_name (str): The name of the client (e.g., "whatsapp")
        websocket_url (str): The base URL of the Ikigai WebSocket endpoint.
        token (str): The API token for authentication.
        connection_timeout (int): The timeout for WebSocket connections.
    """

    def __init__(
        self,
        whatsapp_client: WhatsApp,
        platform_name: str = settings.CLIENT_NAME,
        websocket_url: str = settings.IKIGAI_WEBSOCKET_URL,
        token: str = settings.IKIGAI_API_KEY,
        connection_timeout: int = 10,
    ):
        super().__init__(whatsapp_client)
        self.platform_name = platform_name
        self.websocket_url = websocket_url
        self.token = token
        self.connection_timeout = connection_timeout
        self.connections: Dict[str, websockets.connect] = {}

    async def _get_or_create_connection(self, user_id: str) -> Tuple[websockets.connect, bool]:
        """
        Get or create a WebSocket connection for the specified user.
        If the connection already exists, it returns the existing connection.
        """
        if user_id not in self.connections:
            connection = await websockets.connect(
                f"{self.websocket_url}/websocket/platform/{self.platform_name}/user/{user_id}",
                additional_headers={settings.IKIGAI_API_KEY_HEADER_NAME: self.token},
                close_timeout=self.connection_timeout,
            )
            self.connections[user_id] = connection
            asyncio.create_task(self._listen_to_connection(connection, user_id))
            return connection, True
        return self.connections[user_id], False

    async def _on_error(self, user_id: str, error: Exception):
        """Handle errors that occur during WebSocket communication."""
        self.connections.pop(user_id, None)
        raise error

    async def _on_close(self, user_id: str):
        """Remove the closed connection from the connections dictionary."""
        logger.info("Closed websocket connection for user %s", user_id)
        self.connections.pop(user_id, None)

    async def _on_open(self, user_id: str):
        """Handle the opening of a WebSocket connection."""
        logger.info("Opened websocket connection for user %s", user_id)

    async def _listen_to_connection(self, connection: websockets.connect, user_id: str):
        """
        Listen to the WebSocket connection and handle incoming messages.
        """
        try:
            await self._on_open(user_id)
            async for response in connection:
                response = json.loads(response)
                await self.add_response_to_queue(user_id, response)
        except websockets.ConnectionClosed:
            await self._on_close(user_id)
        except Exception as e:  # pylint: disable=W0718
            await self._on_error(user_id, e)
        await self._on_close(user_id)

    async def post_message_to_server(self, message: Message, is_retry: bool = False):
        """
        Serialize an incoming message event and send it to the server via WebSocket.
        """
        try:
            connection, _ = await self._get_or_create_connection(message.from_user.wa_id)
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
        """
        Serialize an incoming button click event and send it to the server via WebSocket.
        """
        try:
            connection, _ = await self._get_or_create_connection(button_data.from_user.wa_id)
            json_message = json.dumps(self.serialize_button_click(button_data))
            await connection.send(json_message)
        except websockets.exceptions.ConnectionClosed as e:
            if is_retry:
                raise e
            self.connections.pop(button_data.from_user.wa_id, None)
            await self.post_button_click_to_server(button_data, is_retry=True)
