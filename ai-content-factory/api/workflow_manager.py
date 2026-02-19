from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any


class WorkflowManager:
    def __init__(self, workflows_dir: Path, characters_file: Path) -> None:
        self.workflows_dir = workflows_dir
        self.characters_file = characters_file
        self.characters = self._load_json(characters_file)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_workflow(self, name: str) -> dict[str, Any]:
        return self._load_json(self.workflows_dir / name)

    def _resolve_character(self, character: str) -> dict[str, Any]:
        char_key = character.strip().lower()
        if char_key not in self.characters:
            raise ValueError(f"Unknown character '{character}'")
        return self.characters[char_key]

    def build_image_workflow(self, prompt: str, character: str) -> dict[str, Any]:
        char_cfg = self._resolve_character(character)
        workflow = copy.deepcopy(self._load_workflow("z_image.json"))

        prompt_text = f"{char_cfg['trigger']}, {prompt.strip()}"
        workflow["3"]["inputs"]["text"] = prompt_text
        workflow["4"]["inputs"]["lora_name"] = char_cfg["lora"]
        workflow["4"]["inputs"]["strength_model"] = char_cfg["weight"]
        workflow["4"]["inputs"]["strength_clip"] = char_cfg["weight"]
        workflow["6"]["inputs"]["seed"] = random.randint(1, 2**31 - 1)

        return workflow

    def build_video_workflow(
        self,
        image_filename: str,
        video_filename: str,
        character: str,
    ) -> dict[str, Any]:
        char_cfg = self._resolve_character(character)
        workflow = copy.deepcopy(self._load_workflow("wan22_animate.json"))

        workflow["2"]["inputs"]["image"] = image_filename
        workflow["3"]["inputs"]["video"] = video_filename
        workflow["4"]["inputs"]["lora_name"] = char_cfg["lora"]
        workflow["4"]["inputs"]["strength_model"] = char_cfg["weight"]
        workflow["4"]["inputs"]["strength_clip"] = char_cfg["weight"]
        workflow["5"]["inputs"]["text"] = char_cfg["trigger"]
        workflow["6"]["inputs"]["seed"] = random.randint(1, 2**31 - 1)

        return workflow
