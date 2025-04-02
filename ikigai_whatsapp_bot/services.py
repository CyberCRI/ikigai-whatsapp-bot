import asyncio
import json
import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple

import httpx
import websockets
from pywa_async import filters as pywa_filters
from pywa_async import WhatsApp
from pywa_async.types import Button, CallbackButton, Message
from pywa_async.types.sent_message import SentMessage

from enums import Events, ResponseTypes
from schemas import ButtonData
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

    Methods:

    """

    def __init__(self, whatsapp_client: WhatsApp):
        self.whatsapp_client = whatsapp_client
        self.user_queues: Dict[str, asyncio.Queue] = {}
        self.user_tasks: Dict[str, asyncio.Task] = {}

    async def _wait_for_message_to_be_sent(self, message: SentMessage, timeout: int = 10):
        """Wait for the message to be sent to avoid out of order messages."""
        await message._client.listen(
            to=message.recipient,
            sent_to_phone_id=message.sender,
            filters=pywa_filters.update_id(message.id) & pywa_filters.sent,
            cancelers=None,
            timeout=timeout,
        )

    async def _send_text(
        self, user_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        """Send a text message with optional buttons to a user."""
        sent_message = await self.whatsapp_client.send_message(user_id, text, buttons=buttons)
        await self._wait_for_message_to_be_sent(sent_message)

    async def _send_image(
        self, user_id: str, image: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        """Send an image with optional buttons to a user."""
        sent_image = await self.whatsapp_client.send_image(user_id, image, buttons=buttons)
        await self._wait_for_message_to_be_sent(sent_image)

    async def _send_video(
        self, user_id: str, video: str, buttons: Optional[List[Dict[str, str]]] = None
    ):
        """Send a video with optional buttons to a user."""
        sent_video = await self.whatsapp_client.send_video(user_id, video, buttons=buttons)
        await self._wait_for_message_to_be_sent(sent_video)

    async def _send_message_to_user(self, response: Dict[str, Any]):
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

    async def _send_image_to_user(self, response: Dict[str, Any]):
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
            await self._send_image(receiver, image, buttons)

    async def _send_static_image_to_user(self, response: Dict[str, Any]):
        images: List[str] = response.get("images", [])
        response["images"] = [
            f"{settings.IKIGAI_STATIC_FILES_URL}/{image.replace(settings.IKIGAI_SERVER_ROOT_PATH, '')}"
            for image in images
        ]
        await self._send_image_to_user(response)

    async def _send_static_gifs_to_user(self, response: Dict[str, Any]):
        receiver = response["receiver"]["platform_ids"][settings.IKIGAI_WEBSOCKET_PLATFORM_NAME]
        gifs: List[str] = response.get("images", [])
        buttons = response.get("buttons", [])
        gifs = [
            f"{settings.IKIGAI_STATIC_FILES_URL}/{gif.replace(settings.IKIGAI_SERVER_ROOT_PATH, '')}"
            for gif in gifs
        ]
        for gif in gifs:
            await self._send_video(receiver, gif, buttons)

    async def _add_role_to_user(self, response: Dict[str, Any]):
        pass

    async def _remove_role_from_user(self, response: Dict[str, Any]):
        pass

    async def _start_typing(self, response: Dict[str, Any]):
        pass

    async def _stop_typing(self, response: Dict[str, Any]):
        pass

    async def _handle_response(self, action: str, content: Dict[str, Any]):
        match action:
            case ResponseTypes.MESSAGE.value:
                await self._send_message_to_user(content)
            case ResponseTypes.IMAGES.value:
                await self._send_image_to_user(content)
            case ResponseTypes.STATIC_IMAGES.value:
                await self._send_static_image_to_user(content)
            case ResponseTypes.STATIC_GIFS.value:
                await self._send_static_gifs_to_user(content)
            case ResponseTypes.ADD_ROLE.value:
                await self._add_role_to_user(content)
            case ResponseTypes.REMOVE_ROLE.value:
                await self._remove_role_from_user(content)
            case ResponseTypes.START_TYPING.value:
                await self._start_typing(content)
            case ResponseTypes.STOP_TYPING.value:
                await self._stop_typing(content)

    def _get_or_create_queue(self, user_id: str) -> asyncio.Queue:
        """
        Get or create a queue for the specified user.
        """
        if user_id not in self.user_queues:
            self.user_queues[user_id] = asyncio.Queue()
            self.user_tasks[user_id] = asyncio.create_task(self._process_queue(user_id))
        return self.user_queues[user_id]

    async def _process_queue(self, user_id: str):
        """
        Process the message queue for a specific user.
        """
        queue = self.user_queues[user_id]
        while True:
            task = await queue.get()
            try:
                await self._handle_response(task["action"], task["content"])
            except Exception as e:
                logger.error("Failed to process task %s for user %s: %s", task, user_id, str(e))
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

    async def on_error(self, user_id: str, error: Exception):
        self.connections.pop(user_id, None)
        raise error

    async def on_close(self, user_id: str):
        logger.info("Closed websocket connection for user %s", user_id)
        self.connections.pop(user_id, None)

    async def on_open(self, user_id: str):
        logger.info("Opened websocket connection for user %s", user_id)

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
            await self.on_open(user_id)
            async for response in connection:
                response = json.loads(response)
                await self.add_response_to_queue(user_id, response)
        except websockets.ConnectionClosed:
            await self.on_close(user_id)
        except Exception as e:
            await self.on_error(user_id, e)
        await self.on_close(user_id)
