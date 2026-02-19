from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ComfyClient:
    def __init__(self, base_url: str, output_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    async def close(self) -> None:
        await self.client.aclose()

    async def queue_prompt(self, workflow: dict[str, Any]) -> str:
        response = await self.client.post(f"{self.base_url}/prompt", json={"prompt": workflow})
        response.raise_for_status()
        data = response.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"Unexpected ComfyUI response: {data}")
        return prompt_id

    async def wait_for_completion(self, prompt_id: str, poll_interval: float = 1.5) -> dict[str, Any]:
        while True:
            response = await self.client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()
            if prompt_id in history:
                return history[prompt_id]
            await asyncio.sleep(poll_interval)

    def find_output_path(self, history_item: dict[str, Any]) -> str:
        outputs = history_item.get("outputs", {})
        for node_data in outputs.values():
            images = node_data.get("images", [])
            if images:
                image = images[0]
                filename = image.get("filename")
                subfolder = image.get("subfolder", "")
                if filename:
                    return str((self.output_dir / subfolder / filename).resolve())

            gifs = node_data.get("gifs", [])
            if gifs:
                gif = gifs[0]
                filename = gif.get("filename")
                subfolder = gif.get("subfolder", "")
                if filename:
                    return str((self.output_dir / subfolder / filename).resolve())

            videos = node_data.get("videos", [])
            if videos:
                video = videos[0]
                filename = video.get("filename")
                subfolder = video.get("subfolder", "")
                if filename:
                    return str((self.output_dir / subfolder / filename).resolve())

        raise RuntimeError("ComfyUI completed job but no output files were discovered in history")
