from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    BUTTON = "button"
    FILE = "file"
