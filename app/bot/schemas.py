from typing import Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    username: str


class Chat(BaseModel):
    id: int
    type: Literal["private", "group", "supergroup", "channel"] = "group"


class Message(BaseModel):
    message_id: int
    text: str | None = None
    chat: Chat
    from_: User = Field(alias="from")


class CallbackQuery(BaseModel):
    id: str
    from_: User = Field(alias="from")
    data: str
    message: Message


class TelegramUpdate(BaseModel):
    update_id: int
    message: Message | None = None
    callback_query: CallbackQuery | None = None
