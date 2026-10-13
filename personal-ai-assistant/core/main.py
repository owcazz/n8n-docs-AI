"""Main entry point - wires everything together and starts the bot."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from core.agent import Agent
from core.memory import Memory
from plugins.notebook import NotebookPlugin
from plugins.email_manager import EmailPlugin
from plugins.task_manager import TaskManagerPlugin
from plugins.obsidian import ObsidianPlugin
from plugins.youtube import YouTubePlugin
from telegram.bot import TelegramBot

console = Console()


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run():
    """Initialize all components and start the bot."""
    # Load settings
    os.chdir(PROJECT_ROOT)
    settings = Settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    console.print(Panel.fit(
        "[bold cyan]PAI - Personal AI Assistant[/]\n"
        "[dim]Powered by Claude + Telegram[/]",
        border_style="cyan",
    ))

    # Ensure data directory exists
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    # Initialize memory
    memory = Memory(settings.database_path)
    await memory.initialize()
    console.print("  [green]✓[/] Memory database initialized")

    # Initialize agent
    agent = Agent(
        api_key=settings.anthropic_api_key,
        memory=memory,
    )
    console.print("  [green]✓[/] AI Agent initialized")

    # Register plugins
    NotebookPlugin(agent.registry, memory=memory)
    console.print("  [green]✓[/] Notebook plugin loaded")

    EmailPlugin(
        agent.registry,
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
    )
    console.print("  [green]✓[/] Email plugin loaded")

    TaskManagerPlugin(agent.registry, todoist_token=settings.todoist_api_token)
    console.print("  [green]✓[/] Task Manager plugin loaded")

    ObsidianPlugin(agent.registry, vault_path=settings.obsidian_vault_path)
    console.print("  [green]✓[/] Obsidian plugin loaded")

    YouTubePlugin(agent.registry)
    console.print("  [green]✓[/] YouTube analyzer loaded")

    console.print(f"\n  [bold]Registered tools:[/] {len(agent.registry.tools)}")
    for name in agent.registry.tools:
        console.print(f"    • {name}")

    # Start Telegram bot
    console.print("\n  [yellow]Starting Telegram bot...[/]")
    bot = TelegramBot(
        token=settings.telegram_bot_token,
        agent=agent,
        allowed_users=settings.telegram_allowed_users,
    )
    app = bot.build_application()

    console.print("  [bold green]✓ PAI is running! Send a message on Telegram.[/]\n")
    logger.info("PAI started with %d tools", len(agent.registry.tools))

    # Run the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n  [yellow]Shutting down...[/]")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await memory.close()
        console.print("  [green]✓ PAI stopped gracefully.[/]")


def main():
    """Entry point."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
