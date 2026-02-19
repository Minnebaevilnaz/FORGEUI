from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.keyboards import CHARACTER_KB, CONTENT_TYPE_KB
from bot.states import GenerationState

router = Router()
logger = logging.getLogger(__name__)
TMP_DIR = Path("/tmp/ai_content_factory")
TMP_DIR.mkdir(parents=True, exist_ok=True)


def _is_allowed(user_id: int, whitelist: set[int]) -> bool:
    return not whitelist or user_id in whitelist


@router.message(F.text == "/start")
async def start_command(message: Message, state: FSMContext) -> None:
    whitelist = message.bot["config"].whitelist
    if not _is_allowed(message.from_user.id, whitelist):
        await message.answer("Access denied.")
        return

    await state.clear()
    await state.set_state(GenerationState.choosing_type)
    await message.answer("Choose content type:", reply_markup=CONTENT_TYPE_KB)


@router.callback_query(GenerationState.choosing_type, F.data.startswith("type:"))
async def content_type_selected(callback: CallbackQuery, state: FSMContext) -> None:
    content_type = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(content_type=content_type)
    await state.set_state(GenerationState.choosing_character)
    await callback.message.edit_text("Choose character:", reply_markup=CHARACTER_KB)
    await callback.answer()


@router.callback_query(GenerationState.choosing_character, F.data.startswith("char:"))
async def character_selected(callback: CallbackQuery, state: FSMContext) -> None:
    character = callback.data.split(":", maxsplit=1)[1]
    data = await state.get_data()
    content_type = data.get("content_type")
    await state.update_data(character=character)

    if content_type == "image":
        await state.set_state(GenerationState.waiting_prompt)
        await callback.message.edit_text("Send your prompt text for image generation.")
    else:
        await state.set_state(GenerationState.waiting_image)
        await callback.message.edit_text("Send a source image.")

    await callback.answer()


@router.message(GenerationState.waiting_prompt, F.text)
async def process_image_prompt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    character = data["character"]
    cfg = message.bot["config"]

    status_message = await message.answer("⏳ Generating image...")

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{cfg.api_base_url}/generate/image",
                json={"prompt": message.text, "character": character},
            )
            response.raise_for_status()
            payload = response.json()

        output_path = Path(payload["output_path"])
        file_bytes = output_path.read_bytes()
        await message.answer_photo(BufferedInputFile(file_bytes, filename=output_path.name))
        await status_message.edit_text("✅ Image ready.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Image generation flow failed")
        await status_message.edit_text(f"❌ Failed: {exc}")
    finally:
        await state.clear()


@router.message(GenerationState.waiting_image, F.photo)
async def process_video_image(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_path = TMP_DIR / f"{photo.file_unique_id}.jpg"
    await message.bot.download_file(file.file_path, destination=image_path)

    await state.update_data(image_path=str(image_path))
    await state.set_state(GenerationState.waiting_video)
    await message.answer("Now send a reference video.")


@router.message(GenerationState.waiting_video, F.video)
async def process_video_generation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    character = data["character"]
    image_path = Path(data["image_path"])

    video = message.video
    file = await message.bot.get_file(video.file_id)
    ext = mimetypes.guess_extension(video.mime_type or "video/mp4") or ".mp4"
    video_path = TMP_DIR / f"{video.file_unique_id}{ext}"
    await message.bot.download_file(file.file_path, destination=video_path)

    status_message = await message.answer("⏳ Generating video...")
    cfg = message.bot["config"]

    try:
        async with httpx.AsyncClient(timeout=1800) as client:
            with image_path.open("rb") as image_file, video_path.open("rb") as video_file:
                response = await client.post(
                    f"{cfg.api_base_url}/generate/video",
                    data={"character": character},
                    files={
                        "image": (image_path.name, image_file, "image/jpeg"),
                        "video": (video_path.name, video_file, "video/mp4"),
                    },
                )
                response.raise_for_status()
                payload = response.json()

        output_path = Path(payload["output_path"])
        await message.answer_video(BufferedInputFile(output_path.read_bytes(), filename=output_path.name))
        await status_message.edit_text("✅ Video ready.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Video generation flow failed")
        await status_message.edit_text(f"❌ Failed: {exc}")
    finally:
        await state.clear()
        await asyncio.to_thread(image_path.unlink, missing_ok=True)
        await asyncio.to_thread(video_path.unlink, missing_ok=True)


@router.message(GenerationState.waiting_image)
async def waiting_image_fallback(message: Message) -> None:
    await message.answer("Please send an image file.")


@router.message(GenerationState.waiting_video)
async def waiting_video_fallback(message: Message) -> None:
    await message.answer("Please send a video file.")
