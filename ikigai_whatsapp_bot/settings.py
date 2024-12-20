from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the project."""

    # Local settings
    WHATSAPP_BOT_HOST: str = "http://localhost:8080"
    WHATSAPP_VERIFY_TOKEN: str = "verify-token"

    # Ikigai API settings
    IKIGAI_API_URL: str = "http://electro:8000"
    IKGAI_API_TOKEN: str

    # HTTPX settings
    HTTPX_CLIENT_DEFAULT_TIMEOUT: int = 60
    HTTPX_CLIENT_VERIFY_SSL: bool = True

    # WhatsApp API settings
    WHATSAPP_API_URL: str = "https://graph.facebook.com"
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_APP_ID: str
    WHATSAPP_APP_SECRET: str

    class Config:
        env_file = ".env"


settings = Settings()
