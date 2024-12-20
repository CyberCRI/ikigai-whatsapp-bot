from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the project."""

    IKIGAI_API_URL: str = "http://electro:8000"
    IKGAI_API_TOKEN: str

    HTTPX_CLIENT_DEFAULT_TIMEOUT: int = 60
    HTTPX_CLIENT_VERIFY_SSL: bool = True

    WHATSAPP_API_URL: str = "https://graph.facebook.com"
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str

    class Config:
        env_file = ".env"


settings = Settings()
