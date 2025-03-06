import logging
from websocket import create_connection

from fastapi import FastAPI
from pywa_async import WhatsApp
from pywa_async.types import Button, CallbackButton, Message, User

from __version__ import __version__
from client import IkigaiAPIClient, AsyncIkigaiWebSocketClient
from data_types import ButtonData, APIResponse
from enums import MessageType
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

socket_client = AsyncIkigaiWebSocketClient(
    whatsapp_client=whatsapp,
    websocket_url=settings.IKIGAI_WEBSOCKET_URL
)


# @whatsapp.on_message
# async def on_message_backup(client: WhatsApp, message: Message):
#     """
#     Handle incoming messages from WhatsApp.

#     Args:
#         client (WhatsApp): The WhatsApp client.
#         message (Message): The incoming message.
#     """
#     ikigai_client = IkigaiAPIClient()
#     try:
#         response = await ikigai_client.post_message(message)
#         logger.info("Response from Ikigai API: %s", response)
#     except Exception as e:
#         logger.error("Error posting message to Ikigai API: %s", e)

#     buttons = [
#         Button(
#             title=f"Test {i}", callback_data=ButtonData(
#                 user_id=message.from_user.wa_id,
#                 button_id=i
#             )
#         )
#         for i in range(3)
#     ]
#     for m in response["messages"]:
#         await client.send_message(message.from_user.wa_id, m["content"])
#     await client.send_message(message.from_user.wa_id, "buuuuuuuttons", buttons=buttons)



@whatsapp.on_message
async def on_message(client: WhatsApp, message: Message):
    await socket_client.send_message(message)


# @whatsapp.on_callback_button(factory=ButtonData)
# async def on_user_data(client: WhatsApp,  button: CallbackButton[ButtonData]): # type: ignore
#     """
#     Handle incoming callback buttons from WhatsApp.

#     Args:
#         client (WhatsApp): The WhatsApp client.
#         button (CallbackButton): The incoming callback button.

#     Returns:
#         dict: The response and status
#     """
#     ikigai_client = IkigaiAPIClient()
#     try:
#         response = await ikigai_client.post_interaction(button.data)
#         logger.info("Response from Ikigai API: %s", response)
#     except Exception as e:
#         logger.error("Error posting interaction to Ikigai API: %s", e)
#     button_data = button.data
#     return await client.send_message(
#         button.from_user.wa_id,
#         f"User {button_data.user_id} clicked button {button_data.button_id}",
#     )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
