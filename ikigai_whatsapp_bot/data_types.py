from typing import List, Union
from pywa.types import CallbackData
from dataclasses import dataclass

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
    type: MessageType
    data: Union[Message, List[Button], Image, File]


@dataclass(frozen=True, slots=True)
class APIResponse:
    elements: List[APIResponseElement]
