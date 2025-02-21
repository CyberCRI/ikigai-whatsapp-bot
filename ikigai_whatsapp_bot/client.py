from typing import Any, Dict

import httpx
from pywa_async.types import Message

from data_types import ButtonData
from settings import settings


class IkigaiAPIClient:
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
        payload = {
            "id": 10000000,  # message.id
            "content": message.text,
            "author": {
                "id": 5000,  # message.from_user.wa_id,
                "username": message.from_user.name,
                "discriminator": "0",
                "avatar": {"url": ""},
            },
            "channel": {
                "id": 5000,  # message.from_user.wa_id,
                "name": "DM",
                "type": 1,
                "guild": None,
                "used_for": None,
            },
            "created_at": str(message.timestamp.isoformat()),
            "edited_at": None,
        }
        return await self.post("message", payload=payload)
    
    async def post_interaction(self, callback_data: ButtonData) -> httpx.Response:
        """
        Format and post a ButtonData object to the API.

        Args:
            callback_data (ButtonData): The data to post.

        Returns:
            dict: The response from the API.
        """
        payload = {
            "user_id": callback_data.user_id,
            "button_id": callback_data.button_id,
        }
        return await self.post("interaction", payload=payload)
