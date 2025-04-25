import asyncio
import json
from typing import Any

import aiohttp

from app.app import app, setup_app
from app.core.manager import RabbitMQManager


async def handle_message(msg):
    async with msg.process():
        try:
            payload = json.loads(msg.body)
            method_url = payload["method"]
            data = payload.get("data", {})

            async with aiohttp.ClientSession() as session:
                async with session.post(method_url, json=data) as resp:
                    response_data: dict[str, Any] = await resp.json()

                    if not response_data.get("ok"):
                        raise RuntimeError(f"Telegram API error: {response_data}")
        except Exception as e:
            raise RuntimeError("[sender] Exception while processing message") from e


async def main():
    rabbit = RabbitMQManager(
        amqp_url=app.config.rabbitmq.url,
        queue_name=app.config.rabbitmq.output_queue,
    )
    await rabbit.connect()
    await rabbit.consume(handle_message)

    await asyncio.Event().wait()


if __name__ == "__main__":
    setup_app()
    asyncio.run(main())
