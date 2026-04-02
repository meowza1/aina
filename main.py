import asyncio
import os
import threading
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
import uvicorn

load_dotenv()

MODEL_REPO = os.getenv("MODEL_REPO", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
MODEL_FILE = os.getenv("MODEL_FILE", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
MODEL_CTX = int(os.getenv("MODEL_CTX", "2048"))
MODEL_THREADS = int(os.getenv("MODEL_THREADS", "4"))
MODEL_GPU_LAYERS = int(os.getenv("MODEL_GPU_LAYERS", "0"))
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_PREFIX = os.getenv("DISCORD_PREFIX", "!")
DISCORD_ALLOWED_CHANNELS = {
    c.strip() for c in os.getenv("DISCORD_ALLOWED_CHANNELS", "").split(",") if c.strip()
}
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a concise, helpful assistant for a Discord community.",
)

app = FastAPI(title="Railway LLM Discord Bot", version="0.1.0")


class LLMService:
    def __init__(self) -> None:
        self._llm: Optional[Llama] = None
        self._lock = threading.Lock()

    def _load(self) -> None:
        model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
        self._llm = Llama(
            model_path=model_path,
            n_ctx=MODEL_CTX,
            n_threads=MODEL_THREADS,
            n_gpu_layers=MODEL_GPU_LAYERS,
            verbose=False,
        )

    def ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        with self._lock:
            if self._llm is None:
                self._load()

    def chat(self, message: str, username: str = "user") -> str:
        self.ensure_loaded()
        assert self._llm is not None

        output = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"{username}: {message}",
                },
            ],
            temperature=0.7,
            top_p=0.9,
            max_tokens=300,
        )
        return output["choices"][0]["message"]["content"].strip()


llm_service = LLMService()


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=DISCORD_PREFIX, intents=intents)


@bot.event
async def on_ready() -> None:
    print(f"Discord bot online as {bot.user}")


@bot.command(name="chat")
async def chat_command(ctx: commands.Context, *, prompt: str) -> None:
    if DISCORD_ALLOWED_CHANNELS and str(ctx.channel.id) not in DISCORD_ALLOWED_CHANNELS:
        return
    async with ctx.typing():
        response = await asyncio.to_thread(llm_service.chat, prompt, str(ctx.author))
    await ctx.reply(response[:1900])


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    if DISCORD_ALLOWED_CHANNELS and str(message.channel.id) not in DISCORD_ALLOWED_CHANNELS:
        return

    if bot.user and bot.user in message.mentions:
        prompt = message.content.replace(f"<@{bot.user.id}>", "").strip() or "Hello"
        async with message.channel.typing():
            response = await asyncio.to_thread(llm_service.chat, prompt, str(message.author))
        await message.reply(response[:1900])

    await bot.process_commands(message)


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "railway-llm-discord-bot",
            "model_repo": MODEL_REPO,
            "model_file": MODEL_FILE,
        }
    )


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"status": "healthy"})


@app.get("/chat")
def http_chat(q: str, user: str = "http-user") -> JSONResponse:
    answer = llm_service.chat(q, user)
    return JSONResponse({"answer": answer})


async def run_discord() -> None:
    if not DISCORD_TOKEN:
        print("DISCORD_BOT_TOKEN not set; Discord bot is disabled.")
        return
    await bot.start(DISCORD_TOKEN)


async def run_api() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(run_api(), run_discord())


if __name__ == "__main__":
    asyncio.run(main())
