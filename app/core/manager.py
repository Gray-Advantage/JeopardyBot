from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika import Message
from aio_pika.abc import AbstractIncomingMessage


class RabbitMQManager:
    def __init__(self, amqp_url: str, queue_name: str):
        self._url = amqp_url
        self._queue_name = queue_name
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._queue: aio_pika.abc.AbstractQueue | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def send(self, body: bytes) -> None:
        if self._channel is None:
            raise RuntimeError("RabbitMQManager is not connected")
        await self._channel.default_exchange.publish(
            Message(body=body),
            routing_key=self._queue_name,
        )

    async def consume(
        self,
        handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
    ) -> None:
        if self._queue is None:
            raise RuntimeError("RabbitMQManager is not connected")
        await self._queue.consume(handler)
