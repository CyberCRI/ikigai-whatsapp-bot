import logging

from fastapi import FastAPI
from pywa_async import WhatsApp
from pywa_async.types import CallbackButton, Message

from __version__ import __version__
from enums import ServerConnexions
from schemas import ButtonData
from services import APIService, WebSocketService
from settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ikigai Whatsapp bot",
    description="The Ikigai whatsapp bot that processes messages.",
    version=__version__,
)


whatsapp = WhatsApp(
    phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
    token=settings.WHATSAPP_ACCESS_TOKEN,
    api_version=settings.WHATSAPP_API_VERSION,
    server=app,
    callback_url=settings.WHATSAPP_BOT_HOST,
    verify_token=settings.WHATSAPP_VERIFY_TOKEN,
    app_id=settings.WHATSAPP_APP_ID,
    app_secret=settings.WHATSAPP_APP_SECRET,
)

websocket_service = WebSocketService(
    whatsapp_client=whatsapp,
    platform_name=settings.CLIENT_NAME,
    websocket_url=settings.IKIGAI_WEBSOCKET_URL,
    token=settings.IKIGAI_API_KEY,
)

api_service = APIService(
    whatsapp_client=whatsapp,
    platform_name=settings.CLIENT_NAME,
    api_url=settings.IKIGAI_API_URL,
    token=settings.IKIGAI_API_KEY,
)


@whatsapp.on_message
async def on_message(_: WhatsApp, message: Message):
    if settings.SERVER_CONNECTION == ServerConnexions.API.value:
        await api_service.post_message_to_server(message)
    elif settings.SERVER_CONNECTION == ServerConnexions.WEBSOCKET.value:
        await websocket_service.post_message_to_server(message)
    else:
        raise ValueError(f"Invalid server connection type: {settings.SERVER_CONNECTION}")


@whatsapp.on_callback_button(factory=ButtonData)
async def on_callback_button(_: WhatsApp, button: CallbackButton[ButtonData]):
    if settings.SERVER_CONNECTION == ServerConnexions.API.value:
        await api_service.post_button_click_to_server(button)
    elif settings.SERVER_CONNECTION == ServerConnexions.WEBSOCKET.value:
        await websocket_service.post_button_click_to_server(button)
    else:
        raise ValueError(f"Invalid server connection type: {settings.SERVER_CONNECTION}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
