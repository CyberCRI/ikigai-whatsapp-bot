from pydantic_settings import BaseSettings

from enums import ServerConnexions


class Settings(BaseSettings):
    """Settings for the project."""

    # General settings
    EMPTY_MESSAGE_CONTENT: str = "_"
    CLIENT_NAME: str = "whatsapp"
    SERVER_CONNECTION: str = ServerConnexions.WEBSOCKET.value
    QUEUE_TASK_TIMEOUT: int = 10

    # Ikigai API settings
    IKIGAI_API_URL: str = "http://ikigai-server:8000"
    IKIGAI_WEBSOCKET_URL: str = "ws://ikigai-server:8000"
    IKIGAI_API_KEY_HEADER_NAME: str = "x-api-key"
    IKIGAI_API_KEY: str = "server-token"

    # HTTPX settings
    HTTPX_CLIENT_DEFAULT_TIMEOUT: int = 60
    HTTPX_CLIENT_VERIFY_SSL: bool = True

    # Whatsapp API
    WHATSAPP_API_VERSION: float = 21.0
    WHATSAPP_APP_ID: str
    WHATSAPP_APP_SECRET: str
    WHATSAPP_BOT_HOST: str
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str

    class Config:
        extra = "ignore"


settings = Settings()
