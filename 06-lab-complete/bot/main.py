from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from bot.cog_qa import QACog
from bot.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("class-bot")


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
