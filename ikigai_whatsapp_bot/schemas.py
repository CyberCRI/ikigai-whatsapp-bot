from dataclasses import dataclass
from typing import Dict, Optional

from pydantic import BaseModel
from pywa.types import CallbackData


@dataclass(frozen=True, slots=True)
class ButtonData(CallbackData):
    id: int
    custom_id: str
    style: int
    label: str
    clicked: bool
    remove_after_click: bool


class User(BaseModel):
    id: int
    username: str
    platform_ids: Dict[str, str]


class ButtonResponse(BaseModel):
    id: int
    custom_id: str
    style: int
    label: str
    clicked: bool
    remove_after_click: bool


class Channel(BaseModel):
    id: int
    name: str
    platform_ids: Dict[str, str]


class Guild(BaseModel):
    id: int
    name: str
    platform_ids: Dict[str, str]


class MessageResponse(BaseModel):
    user: Optional[User]
    channel: Optional[Channel]
    message: str
    buttons: list[ButtonResponse]
    delete_after: Optional[int] = None


class ImageResponse(BaseModel):
    user: Optional[User]
    channel: Optional[Channel]
    image: str
    buttons: list[ButtonResponse]
    caption: Optional[str] = None
    delete_after: Optional[int] = None


class RoleResponse(BaseModel):
    user: User
    guild: Optional[Guild]
    role: str


class TypingResponse(BaseModel):
    user: Optional[User]
    channel: Optional[Channel]
