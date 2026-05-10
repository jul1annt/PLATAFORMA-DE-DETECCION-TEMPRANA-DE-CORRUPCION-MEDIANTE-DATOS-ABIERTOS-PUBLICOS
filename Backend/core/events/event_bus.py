import asyncio
from typing import Callable, Awaitable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {}
        self._queue = asyncio.Queue()
        self._worker_task = None

    def subscribe(self, event_type: str, handler: Callable[[Any], Awaitable[None]]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Any):
        await self._queue.put((event_type, payload))

    async def _worker(self):
        while True:
            event_type, payload = await self._queue.get()
            try:
                handlers = self._subscribers.get(event_type, [])
                for handler in handlers:
                    try:
                        await handler(payload)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error in event handler for {event_type}: {e}")
            finally:
                self._queue.task_done()

    def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

event_bus = EventBus()
