from pydantic import BaseModel


class WhatsappMessage(BaseModel):
    phone_number: str
    message: str


class WhatsappResponse(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    type: str = "text"
    preview_url: bool = False
    body: str
    recipient: str

    def to_dict(self):
        return {
            "messaging_product": self.messaging_product,
            "recipient_type": self.recipient_type,
            "to": self.recipient,
            "type": self.type,
            "text": {
                "preview_url": self.preview_url,
                "body": self.body
            },
        }
