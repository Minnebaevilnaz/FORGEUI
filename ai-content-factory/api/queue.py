from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from api.comfy_client import ComfyClient

logger = logging.getLogger(__name__)


@dataclass
class QueueJob:
    payload: dict[str, Any]
    future: asyncio.Future[dict[str, str]]


class GenerationQueue:
    def __init__(self, comfy_client: ComfyClient) -> None:
        self.comfy_client = comfy_client
        self._queue: asyncio.Queue[QueueJob] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker(), name="generation-queue-worker")

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                logger.info("Generation queue worker stopped")
            self._worker_task = None

    async def submit(self, payload: dict[str, Any]) -> dict[str, str]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, str]] = loop.create_future()
        await self._queue.put(QueueJob(payload=payload, future=future))
        return await future

    async def _worker(self) -> None:
        logger.info("Generation queue worker started")
        while True:
            job = await self._queue.get()
            try:
                workflow = job.payload["workflow"]
                prompt_id = await self.comfy_client.queue_prompt(workflow)
                logger.info("Queued ComfyUI prompt id=%s", prompt_id)
                history_item = await self.comfy_client.wait_for_completion(prompt_id)
                output_path = self.comfy_client.find_output_path(history_item)
                result = {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "output_path": output_path,
                }
                if not job.future.done():
                    job.future.set_result(result)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Generation job failed")
                if not job.future.done():
                    job.future.set_exception(exc)
            finally:
                self._queue.task_done()
