from enum import Enum


class Events(Enum):
    """The events that are handled by the server."""

    MESSAGE = "message"
    BUTTON_CLICK = "button_click"
    MEMBER_JOIN = "member_join"
    MEMBER_UPDATE = "member_update"


class ResponseTypes(str, Enum):
    """The actions that can be sent by the server."""

    MESSAGE = "message"
    IMAGE = "image"
    ADD_ROLE = "add_role"
    REMOVE_ROLE = "remove_role"
    START_TYPING = "start_typing"
    STOP_TYPING = "stop_typing"


class ChannelTypes(str, Enum):
    """The types of channels."""

    DM = "dm"
    CHANNEL = "channel"


class ServerConnexions(str, Enum):
    """The types of server connexions."""

    WEBSOCKET = "websocket"
    API = "api"
