import logging

from fastapi import FastAPI
from pywa_async import WhatsApp
from pywa_async.types import Message

from __version__ import __version__
from client import IkigaiAPIClient
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


@whatsapp.on_message
async def on_message(client: WhatsApp, message: Message):
    """
    Handle incoming messages from WhatsApp.

    Args:
        client (WhatsApp): The WhatsApp client.
        message (Message): The incoming message.

    Returns:
        dict: The response and status
    """
    ikigai_client = IkigaiAPIClient()
    try:
        response = await ikigai_client.post_message(message)
        logger.info("Response from Ikigai API: %s", response)
    except Exception as e:
        logger.error("Error posting message to Ikigai API: %s", e)

    # Just send back the message for testing purpose
    await client.send_message(message.from_user.wa_id, message.text)
    return {"status": "ok"}, 200


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
