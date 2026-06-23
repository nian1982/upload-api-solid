import json
from typing import Any, AsyncIterator

import redis.asyncio as aioredis

from ws.config import WSSettings
from shared.logger import log

logger = log("solid.ws")


class RedisProgressSubscriber:
    def __init__(self, settings: WSSettings | None = None):
        self._settings = settings or WSSettings()
        self._client: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._settings.redis_url,
            socket_connect_timeout=5,
            socket_timeout=10,
        )
        self._pubsub = self._client.pubsub()

    async def subscribe(self, channel: str) -> None:
        if not self._pubsub:
            await self.connect()
        await self._pubsub.subscribe(channel)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        if not self._pubsub:
            return
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    yield json.loads(data.decode())
                elif isinstance(data, str):
                    yield json.loads(data)

    async def get_state(self, key: str) -> dict[str, Any] | None:
        if not self._client:
            return None
        data = await self._client.get(key)
        if data:
            return json.loads(data) if isinstance(data, str) else json.loads(data.decode())
        return None

    async def publish(self, channel: str, data: dict[str, Any]) -> None:
        if not self._client:
            return
        payload = json.dumps(data, default=str)
        await self._client.publish(channel, payload)

    async def unsubscribe(self, channel: str) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)

    async def close(self) -> None:
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()
