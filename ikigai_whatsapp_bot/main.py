from typing import Dict

from fastapi import FastAPI
from __version__ import __version__

from models import WhatsappMessage, WhatsappResponse
from clients import IkigaiAPIClient, WhatsappClient


app = FastAPI(
    title="Ikigai Whatsapp bot",
    description="The Ikigai whatsapp bot that processes messages.",
    version=__version__,
)


@app.get("/test")
async def test() -> Dict[str, str]:
    return {"test": "Hello, World!"}, 200


@app.post("/message")
async def message(message: WhatsappMessage) -> Dict[str, str]:
    try:
        api_client = IkigaiAPIClient()
        whatsapp_client = WhatsappClient()
        response = await api_client.post_message(message)
        message = WhatsappResponse(...)
        await whatsapp_client.send_message(message)
        return {"status": "ok"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
