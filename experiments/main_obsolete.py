# pylint: disable=wrong-import-position
"""Main file for running the Discord bot."""
import os
import sys
from pathlib import Path

import discord
from dotenv import load_dotenv
from mergedbots.experimental.two_way_bot import TwoWayBotWrapper
from mergedbots.ext.discord_integration import MergedBotDiscord

load_dotenv()
sys.path.append(str(Path(__file__).parents[1]))
from experiments.common.bot_manager import bot_manager
from experiments.mergedbots_copilot.repo_bots import list_repo_tool

DISCORD_BOT_SECRET = os.environ["DISCORD_BOT_SECRET"]

discord_client = discord.Client(intents=discord.Intents.default())


@discord_client.event
async def on_ready() -> None:
    """Called when the client is done preparing the data received from Discord."""
    print("Logged in as", discord_client.user)
    print()


if __name__ == "__main__":
    two_way_bot_wrapper = TwoWayBotWrapper(
        manager=bot_manager,
        this_bot_handle="TwoWayBot",
        target_bot_handle=list_repo_tool.bot.handle,
        feedback_bot_handle="FeedbackBot",
    )
    MergedBotDiscord(bot=two_way_bot_wrapper.this_bot, discord_client=discord_client)
    discord_client.run(DISCORD_BOT_SECRET)
