import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal, cast

import aiohttp
from aio_pika.abc import AbstractIncomingMessage

from app.bot.schemas import CallbackQuery, Chat, Message, TelegramUpdate
from app.core.manager import RabbitMQManager

if TYPE_CHECKING:
    from app.app import Application


class TelegramBotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self._token = app.config.bot.token
        self._base_url = "https://api.telegram.org/bot"
        self._session: aiohttp.ClientSession | None = None
        self._handlers: list[
            tuple[list[str] | None, Callable[[Message], Awaitable[None]]]
        ] = []
        self._callback_handlers: list[
            tuple[str | None, Callable[[CallbackQuery], Awaitable[None]]]
        ] = []

    def build_method_url(self, method_name: str) -> str:
        return f"{self._base_url}{self._token}/{method_name}"

    async def _mainloop(self) -> None:
        await self.connect()
        rabbit = RabbitMQManager(
            amqp_url=self.app.config.rabbitmq.url,
            queue_name=self.app.config.rabbitmq.input_queue,
        )
        await rabbit.connect()
        await rabbit.consume(self.get_update)

        await asyncio.Event().wait()

    def mainloop(self) -> None:
        asyncio.run(self._mainloop())

    async def connect(self) -> None:
        self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def _post(self, method: str, json: dict[str, Any]) -> dict[Any, Any]:
        if self._session is None:
            raise RuntimeError("TelegramBotManager is not connected")

        async with self._session.post(self.build_method_url(method), json=json) as resp:
            response_data: dict[str, Any] = await resp.json()
            if not response_data.get("ok"):
                raise RuntimeError(f"Telegram API error: {response_data}")
            return cast(dict[Any, Any], response_data["result"])

    async def get_update(self, msg: AbstractIncomingMessage) -> None:
        async with msg.process():
            data = json.loads(msg.body)
            update = TelegramUpdate(**data)

            if update.message and update.message.text:
                text = update.message.text.strip()
                is_command = text.startswith("/")

                for commands, handler in self._handlers:
                    if commands is None and not is_command:
                        await handler(update.message)
                    elif (
                        commands is not None
                        and is_command
                        and any(
                            text.split()[0] == f"/{command}" for command in commands
                        )
                    ):
                        await handler(update.message)
                        return

            elif update.callback_query and update.callback_query.data:
                data = update.callback_query.data
                for expected_data, handler in self._callback_handlers:
                    if expected_data is None or data == expected_data:
                        await handler(update.callback_query)
                        return

    def connect_handler(
        self, commands: list[str] | None = None
    ) -> Callable[
        [Callable[[Message], Awaitable[None]]],
        Callable[[Message], Awaitable[None]],
    ]:
        def decorator(
            func: Callable[[Message], Awaitable[None]],
        ) -> Callable[[Message], Awaitable[None]]:
            self._handlers.append((commands, func))
            return func

        return decorator

    def connect_callback_handler(
        self,
        data_value: str | None = None,
    ) -> Callable[
        [Callable[[CallbackQuery], Awaitable[None]]],
        Callable[[CallbackQuery], Awaitable[None]],
    ]:
        def decorator(
            func: Callable[[CallbackQuery], Awaitable[None]],
        ) -> Callable[[CallbackQuery], Awaitable[None]]:
            self._callback_handlers.append((data_value, func))
            return func

        return decorator

    async def send_message(
        self,
        chat: Chat,
        text: Any,
        keyboard: list[list[tuple[str, str]]] | None = None,
        parse_mode: Literal["MarkdownV2", "HTML", "Markdown"] | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[Any, Any]:
        json_data = {
            "chat_id": chat.id,
            "text": str(text),
        }

        if parse_mode is not None:
            json_data["parse_mode"] = parse_mode

        if keyboard is not None:
            inline_keyboard = [
                [{"text": label, "callback_data": data} for label, data in row]
                for row in keyboard
            ]
            json_data["reply_markup"] = {"inline_keyboard": inline_keyboard}

        if reply_to_message_id is not None:
            json_data["reply_parameters"] = {"message_id": reply_to_message_id}

        return await self._post("sendMessage", json=json_data)

    async def answer_callback_query(
        self,
        callback_query: CallbackQuery,
        text: str = "",
        show_alert: bool = False,
    ) -> dict[Any, Any]:
        payload = {
            "callback_query_id": callback_query.id,
            "text": text,
            "show_alert": show_alert,
        }

        if not text:
            payload.pop("text")

        return await self._post("answerCallbackQuery", json=payload)

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        keyboard: list[list[tuple[str, str]]] | None = None,
        parse_mode: Literal["MarkdownV2", "HTML", "Markdown"] | None = None,
    ) -> dict[Any, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }

        if keyboard:
            inline_keyboard = [
                [{"text": label, "callback_data": data} for label, data in row]
                for row in keyboard
            ]
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

        if parse_mode is not None:
            payload["parse_mode"] = parse_mode

        return await self._post("editMessageText", json=payload)


def setup_bot_api(app: "Application") -> None:
    app.bot_api = TelegramBotManager(app)
