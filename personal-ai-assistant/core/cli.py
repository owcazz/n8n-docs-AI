"""CLI mode - interact with the agent directly in the terminal (no Telegram needed)."""

import asyncio
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

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

console = Console()
CLI_USER_ID = 1  # Local user ID for CLI mode


async def run_cli():
    os.chdir(PROJECT_ROOT)
    settings = Settings()

    console.print(Panel.fit(
        "[bold cyan]PAI - Personal AI Assistant[/] [dim](CLI Mode)[/]\n"
        "[dim]Type 'quit' to exit, 'help' for commands[/]",
        border_style="cyan",
    ))

    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    memory = Memory(settings.database_path)
    await memory.initialize()

    agent = Agent(api_key=settings.anthropic_api_key, memory=memory)

    # Load plugins
    NotebookPlugin(agent.registry, memory=memory)
    EmailPlugin(
        agent.registry,
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
    )
    TaskManagerPlugin(agent.registry, todoist_token=settings.todoist_api_token)
    ObsidianPlugin(agent.registry, vault_path=settings.obsidian_vault_path)
    YouTubePlugin(agent.registry)

    console.print(f"[green]✓[/] Loaded {len(agent.registry.tools)} tools\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]Ty[/]")
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break

        with console.status("[yellow]Myślę...[/]"):
            try:
                response = await agent.process_message(CLI_USER_ID, user_input)
            except Exception as e:
                response = f"❌ Błąd: {e}"

        console.print(Panel(response, title="[bold green]PAI[/]", border_style="green"))

    await memory.close()
    console.print("[dim]Do zobaczenia! 👋[/]")


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
