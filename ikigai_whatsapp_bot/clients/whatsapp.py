from settings import settings
from clients.base import BaseClient
from models import WhatsappResponse


class WhatsappClient(BaseClient):
    """
    Client for interacting with the Whatsapp API

    Args:
        base_url (str): The base URL of the Ikigai API.
        token (str): The API token for the Ikigai API.
        verify_ssl (bool): Whether to verify SSL certificates.
        timeout (int): The timeout for requests.
    """

    def __init__(
        self,
        base_url: str = settings.WHATSAPP_API_URL,
        api_version: str = settings.WHATSAPP_API_VERSION,
        phone_number_id: str = settings.WHATSAPP_PHONE_NUMBER_ID,
        access_token: str = settings.WHATSAPP_ACCESS_TOKEN,
        verify_ssl: bool = settings.HTTPX_CLIENT_VERIFY_SSL,
        timeout: int = settings.HTTPX_CLIENT_DEFAULT_TIMEOUT,
    ):
        url = f"{base_url}/{api_version}/{phone_number_id}"
        super().__init__(url, access_token, verify_ssl, timeout)

    async def send_message(self, message: WhatsappResponse):
        payload = message.to_dict()
        return await self.post("messages", payload)
