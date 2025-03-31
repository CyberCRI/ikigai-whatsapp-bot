from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"


class Events(Enum):
    """The events that are handled by the server."""

    MESSAGE = "message"
    BUTTON_CLICK = "button_click"
    MEMBER_JOIN = "member_join"
    MEMBER_UPDATE = "member_update"


# class ButtonTypes(Enum):
