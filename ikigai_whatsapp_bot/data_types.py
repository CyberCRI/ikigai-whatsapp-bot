from dataclasses import dataclass
from typing import List, Union

from pywa.types import CallbackData

from enums import MessageType


@dataclass(frozen=True, slots=True)
class ButtonData(CallbackData):
    user_id: int
    button_id: str


@dataclass(frozen=True, slots=True)
class Message:
    content: str


@dataclass(frozen=True, slots=True)
class Button:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class Image:
    id: str
    url: str


@dataclass(frozen=True, slots=True)
class File:
    id: str
    mime: str
    url: str


@dataclass(frozen=True, slots=True)
class APIResponseElement:
    message: Message
    images: List[Image]
    files: List[File]
    buttons: List[Button]


@dataclass(frozen=True, slots=True)
class APIResponse:
    elements: List[APIResponseElement]
