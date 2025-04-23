import asyncio
import json
from typing import Any, cast

import aiohttp

from app.app import app, setup_app
from app.core.manager import RabbitMQManager


async def get_updates(url: str, offset: int) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"offset": offset, "timeout": 30}) as resp:
            return cast(dict[str, Any], await resp.json())


async def poll_and_push() -> None:
    rabbit = RabbitMQManager(
        amqp_url=app.config.rabbitmq.url,
        queue_name=app.config.rabbitmq.input_queue,
    )
    await rabbit.connect()

    offset = 0
    while True:
        data = await get_updates(app.bot_api.build_method_url("getUpdates"), offset)
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            await rabbit.send(json.dumps(update).encode())


if __name__ == "__main__":
    setup_app()
    asyncio.run(poll_and_push())
