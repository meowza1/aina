# Railway Small LLM + Discord Bot

A compact, self-hosted Python app that runs:

1. A local GGUF LLM with `llama-cpp-python`
2. A FastAPI web service (for health + chat endpoint)
3. A Discord bot that can read and reply in channels

Designed for Railway deployment with a single service.

## Features

- Local model inference (no paid API required)
- `!chat <message>` command in Discord
- Mention-based replies (`@YourBot hello`) in Discord
- Optional channel allowlist
- `/healthz` endpoint for Railway checks

## Project structure

- `main.py` — FastAPI + Discord bot + LLM runtime
- `requirements.txt` — dependencies
- `Procfile` / `railway.json` — Railway start configuration

## 1) Create your Discord bot

1. Open Discord Developer Portal and create an application.
2. Create a bot under **Bot** tab.
3. Enable **Message Content Intent**.
4. Copy bot token.
5. Under OAuth2 URL Generator, choose scopes:
   - `bot`
6. Bot permissions at minimum:
   - Read Messages/View Channels
   - Send Messages
   - Read Message History
7. Invite bot to your server.

## 2) Railway deploy

1. Push this folder to GitHub.
2. In Railway, create a new project from that repo.
3. Set environment variables:

```bash
DISCORD_BOT_TOKEN=your_token_here
DISCORD_PREFIX=!
DISCORD_ALLOWED_CHANNELS=123456789012345678,234567890123456789
MODEL_REPO=Qwen/Qwen2.5-1.5B-Instruct-GGUF
MODEL_FILE=qwen2.5-1.5b-instruct-q4_k_m.gguf
MODEL_CTX=2048
MODEL_THREADS=4
MODEL_GPU_LAYERS=0
SYSTEM_PROMPT=You are a concise, helpful assistant for a Discord community.
```

`DISCORD_ALLOWED_CHANNELS` is optional. If empty, bot can reply anywhere it can read.

## 3) Use it

- Mention bot in allowed channel: `@BotName explain Docker in simple terms`
- Or use command: `!chat give me a 5-line summary of Rust`

HTTP test:

```bash
GET /chat?q=hello
GET /healthz
```

## Notes

- First request is slower due to model download/load.
- Railway CPU/RAM limits affect speed; the default 1.5B Q4 model is a good small/capable baseline.
- For lower memory use, choose a smaller GGUF model file.
