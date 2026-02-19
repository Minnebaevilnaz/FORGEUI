# AI Content Factory

Local AI content factory that connects Telegram Bot → FastAPI → ComfyUI on a single machine.

## Features

- Telegram bot flow with inline keyboards and FSM
- Character-based dynamic LoRA injection
- Image generation (`z_image.json`)
- Video generation (`wan22_animate.json`)
- Single-worker async queue to protect one GPU
- Local-only API deployment

## Project Structure

```text
ai-content-factory/
├── bot/
│   ├── main.py
│   ├── handlers.py
│   ├── states.py
│   ├── keyboards.py
│   └── config.py
│
├── api/
│   ├── main.py
│   ├── comfy_client.py
│   ├── workflow_manager.py
│   ├── queue.py
│   └── models.py
│
├── workflows/
│   ├── z_image.json
│   └── wan22_animate.json
│
├── characters.json
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

1. Ensure Python 3.10+ is installed.
2. Ensure ComfyUI is running locally and API is enabled.
3. Clone this repository and move into the project root:

```bash
cd ai-content-factory
```

4. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Configure environment variables:

```bash
cp .env.example .env
```

7. Edit `.env`:
- `TELEGRAM_BOT_TOKEN`: your Telegram bot token
- `TELEGRAM_WHITELIST`: comma-separated Telegram user IDs allowed to use the bot
- `API_BASE_URL`: must point to local API (`http://127.0.0.1:8000`)
- `COMFYUI_API_URL`: ComfyUI API endpoint (`http://127.0.0.1:8188`)
- `COMFYUI_INPUT_DIR`: your real ComfyUI `input` folder
- `COMFYUI_OUTPUT_DIR`: your real ComfyUI `output` folder

## Run API

From `ai-content-factory` directory:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

API binds only to localhost for security.

### API Endpoints

- `POST /generate/image`

```json
{
  "prompt": "cinematic portrait",
  "character": "jasmine"
}
```

- `POST /generate/video`
  - multipart fields: `image`, `video`, `character`

## Run Bot

From `ai-content-factory` directory:

```bash
python -m bot.main
```

## Telegram Flow

1. Send `/start`
2. Choose content type (`Image` or `Video`)
3. Choose character (`Olivia` or `Jasmine`)
4. For image: send prompt text
5. For video: send source image, then reference video
6. Bot sends back generated result automatically

## Add New Characters

Edit `characters.json` and add a new entry:

```json
"new_character": {
  "lora": "new_character.safetensors",
  "weight": 1.0,
  "trigger": "NEW_CHARACTER_TRIGGER"
}
```

Requirements:
- `lora` file must exist in ComfyUI LoRA models path
- Character key is used in API/bot requests

## Add New Workflows

1. Put workflow JSON into `workflows/`
2. Update `api/workflow_manager.py` to map the nodes used for:
   - prompt text
   - LoRA name / weight
   - seed
   - media inputs (if needed)
3. Add new API endpoint or route logic in `api/main.py`
4. Update bot handlers to expose the new content type

## Security Notes

- FastAPI is bound to `127.0.0.1` only.
- Bot communicates only with local API URL.
- Use whitelist to restrict Telegram access.
