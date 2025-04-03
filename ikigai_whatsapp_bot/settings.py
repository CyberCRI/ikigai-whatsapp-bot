from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the project."""

    # Ikigai API settings
    IKIGAI_API_URL: str = "http://ikigai-server:8000"
    # Use an exposed url for local development to allow Whatsapp to reach the server
    IKIGAI_STATIC_FILES_URL: str = "http://ikigai-server:8000"
    IKIGAI_WEBSOCKET_URL: str = "ws://ikigai-server:8000"
    IKIGAI_WEBSOCKET_PLATFORM_NAME: str = "whatsapp"
    IKGAI_API_TOKEN: str
    IKIGAI_SERVER_ROOT_PATH: str = "/app"

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
