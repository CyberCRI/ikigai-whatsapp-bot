from dataclasses import dataclass
from typing import Dict, Optional

from pywa.types import CallbackData


@dataclass(frozen=True, slots=True)
class User:
    id: str
    username: str
    discriminator: str
    avatar: Dict[str, str]


@dataclass(frozen=True, slots=True)
class Channel:
    id: str
    name: str
    type: int
    guild_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Message:
    content: str
    author: User
    channel: None = None


@dataclass(frozen=True, slots=True)
class ButtonData(CallbackData):
    id: int
    custom_id: str
    style: int
    label: str
    clicked: bool
    remove_after_click: bool
