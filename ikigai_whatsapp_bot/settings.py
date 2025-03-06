from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the project."""

    # Ikigai API settings
    IKIGAI_API_URL: str = "http://electro:8000"
    IKIGAI_WEBSOCKET_URL: str = "ws://electro:8000"
    IKIGAI_WEBSOCKET_CLIENT_NAME: str = "whatsapp"
    IKGAI_API_TOKEN: str

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
