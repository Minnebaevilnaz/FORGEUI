from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from api.comfy_client import ComfyClient
from api.models import ImageGenerateRequest, JobResult
from api.queue import GenerationQueue
from api.workflow_manager import WorkflowManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = BASE_DIR / "workflows"
CHARACTERS_FILE = BASE_DIR / "characters.json"

COMFYUI_API_URL = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188")
COMFYUI_INPUT_DIR = Path(os.getenv("COMFYUI_INPUT_DIR", str((BASE_DIR / "comfy_input").resolve())))
COMFYUI_OUTPUT_DIR = Path(os.getenv("COMFYUI_OUTPUT_DIR", str((BASE_DIR / "comfy_output").resolve())))

COMFYUI_INPUT_DIR.mkdir(parents=True, exist_ok=True)
COMFYUI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    workflow_manager = WorkflowManager(WORKFLOWS_DIR, CHARACTERS_FILE)
    comfy_client = ComfyClient(COMFYUI_API_URL, COMFYUI_OUTPUT_DIR)
    generation_queue = GenerationQueue(comfy_client)

    app.state.workflow_manager = workflow_manager
    app.state.comfy_client = comfy_client
    app.state.generation_queue = generation_queue

    await generation_queue.start()
    logger.info("API started")
    try:
        yield
    finally:
        await generation_queue.stop()
        await comfy_client.close()
        logger.info("API stopped")


app = FastAPI(title="AI Content Factory API", version="1.0.0", lifespan=lifespan)


def _save_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix
    filename = f"{uuid.uuid4().hex}{suffix}"
    output_path = COMFYUI_INPUT_DIR / filename
    with output_path.open("wb") as f:
        f.write(file.file.read())
    return filename


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate/image", response_model=JobResult)
async def generate_image(request: ImageGenerateRequest) -> JobResult:
    try:
        workflow = app.state.workflow_manager.build_image_workflow(request.prompt, request.character)
        result = await app.state.generation_queue.submit({"workflow": workflow})
        return JobResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}") from exc


@app.post("/generate/video", response_model=JobResult)
async def generate_video(
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    character: str = Form(...),
) -> JobResult:
    image_name = ""
    video_name = ""
    try:
        image_name = _save_upload(image)
        video_name = _save_upload(video)

        workflow = app.state.workflow_manager.build_video_workflow(
            image_filename=image_name,
            video_filename=video_name,
            character=character,
        )
        result = await app.state.generation_queue.submit({"workflow": workflow})
        return JobResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}") from exc
