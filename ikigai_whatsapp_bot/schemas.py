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
    guild: Optional[str]
    used_for: Optional[str]


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    content: str
    author: User
    channel: Channel
    created_at: str
    edited_at: Optional[str]



@dataclass(frozen=True, slots=True)
class ButtonData(CallbackData):
    style: int
    label: str
    custom_id: str
    disabled: bool
    remove_after_click: bool
