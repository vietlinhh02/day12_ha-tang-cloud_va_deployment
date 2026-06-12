from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord.ext import commands

from bot.cog_qa import QACog
from bot.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("class-bot")

# ── Health check server (cho cloud deploy) ──

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/ready"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "Discord Class Bot"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *a): pass  # silent

def _start_health_server():
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()

t = threading.Thread(target=_start_health_server, daemon=True)
t.start()
port = int(os.environ.get("PORT", 8000))
log.info("Health server started on port %d", port)


def create_bot(settings: Settings) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
        await bot.add_cog(QACog(bot, settings))
        try:
            synced = await bot.tree.sync()
            log.info("Synced %d slash commands", len(synced))
        except Exception:
            log.exception("Failed to sync commands")

    return bot


async def run() -> None:
    settings = Settings()
    bot = create_bot(settings)
    await bot.start(settings.discord_token)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
