from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class EventBus:
    def __init__(self) -> None:
        self._topics: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def publish(self, topic: str, event: str, data: dict) -> None:
        for queue in tuple(self._topics.get(topic, ())):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait((event, data))

    @asynccontextmanager
    async def subscribe(self, topic: str) -> AsyncIterator[AsyncIterator[tuple[str, dict]]]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._topics[topic].add(queue)

        async def events() -> AsyncIterator[tuple[str, dict]]:
            while True:
                yield await queue.get()

        try:
            yield events()
        finally:
            self._topics[topic].discard(queue)
            if not self._topics[topic]:
                del self._topics[topic]
