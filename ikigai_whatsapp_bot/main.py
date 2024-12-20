from fastapi import FastAPI
from pywa_async import filters, WhatsApp
from pywa_async.types import CallbackButton, Message

from __version__ import __version__
from client import IkigaiAPIClient
from settings import settings

app = FastAPI(
    title="Ikigai Whatsapp bot",
    description="The Ikigai whatsapp bot that processes messages.",
    version=__version__,
)


whatsapp = WhatsApp(
    phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
    token=settings.WHATSAPP_ACCESS_TOKEN,
    server=app,
    callback_url=settings.WHATSAPP_BOT_HOST,
    verify_token=settings.WHATSAPP_VERIFY_TOKEN,
    app_id=settings.WHATSAPP_APP_ID,
    app_secret=settings.WHATSAPP_APP_SECRET,
)


@whatsapp.on_message()
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
    response = await ikigai_client.post_message(message)
    await client.send_message(message.from_user.wa_id, response["message"])
    return {"status": "ok"}, 200


@whatsapp.on_callback_button(filters.startswith("id"))
def on_button_click(client: WhatsApp, button: CallbackButton):
    """
    Handle button clicks from WhatsApp.

    Args:
        client (WhatsApp): The WhatsApp client.
        button (CallbackButton): The button clicked.

    Returns:
        dict: The response and status
    """
    ikigai_client = IkigaiAPIClient()
    response = ikigai_client.post_message(button)
    client.send_message(button.from_user.wa_id, response["message"])
    return {"status": "ok"}, 200


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(whatsapp, host="0.0.0.0", port=8080)
