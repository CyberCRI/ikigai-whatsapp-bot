import logging

from fastapi import FastAPI
from pywa_async import WhatsApp
from pywa_async.types import CallbackButton, Message

from __version__ import __version__
from data_types import ButtonData
from services import WebSocketService
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
    websocket_url=settings.IKIGAI_WEBSOCKET_URL,
    client_name=settings.IKIGAI_WEBSOCKET_CLIENT_NAME,
)


@whatsapp.on_message
async def on_message(client: WhatsApp, message: Message):
    await websocket_service.send_message(message)


@whatsapp.on_callback_button
def on_callback_button(client: WhatsApp, button: CallbackButton[ButtonData]):
    websocket_service.send_interaction(button)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
