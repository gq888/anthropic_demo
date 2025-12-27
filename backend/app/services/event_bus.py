"""Pub/sub event bus to stream run events to subscribers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import DefaultDict

from app.models.events import RunEvent


class EventBus:
    """Simple in-memory pub/sub for broadcasting RunEvent instances."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, set[asyncio.Queue[RunEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        async with self._lock:
            queues = self._subscribers.get(run_id)
            if not queues:
                return
            queues.discard(queue)
            if not queues:
                self._subscribers.pop(run_id, None)

    async def publish(self, event: RunEvent) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(event.run_id, set()))
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                _ = queue.get_nowait()
                queue.put_nowait(event)


event_bus = EventBus()
