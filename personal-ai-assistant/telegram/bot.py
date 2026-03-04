"""Telegram Bot interface - connects users to the AI agent via Telegram."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.agent import Agent

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that bridges user messages to the AI agent."""

    def __init__(self, token: str, agent: Agent, allowed_users: list[int]):
        self.token = token
        self.agent = agent
        self.allowed_users = allowed_users

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot."""
        if not self.allowed_users:
            return True  # No restrictions if list is empty
        return user_id in self.allowed_users

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        if not self._is_authorized(user.id):
            await update.message.reply_text("⛔ Nie masz uprawnień do korzystania z tego bota.")
            return

        await update.message.reply_text(
            f"👋 Cześć {user.first_name}!\n\n"
            "Jestem PAI - Twój Osobisty Asystent AI.\n\n"
            "Co potrafię:\n"
            "📝 Notatki - zapisuję pomysły i przemyślenia\n"
            "📧 Email - czytam i wysyłam emaile\n"
            "✅ Zadania - zarządzam Twoim Todoist\n"
            "📓 Obsidian - przeszukuję i tworzę notatki\n"
            "🎬 YouTube - analizuję filmy i transkrypcje\n"
            "🧠 Pamięć - pamiętam kontekst rozmów\n\n"
            "Po prostu napisz do mnie naturalnie - ja się domyślę czego potrzebujesz!\n\n"
            "Komendy:\n"
            "/help - pomoc\n"
            "/notes - pokaż notatki\n"
            "/tasks - pokaż zadania\n"
            "/facts - co o Tobie wiem"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update.effective_user.id):
            return

        await update.message.reply_text(
            "🤖 **PAI - Pomoc**\n\n"
            "Możesz pisać do mnie naturalnym językiem, np.:\n\n"
            '📝 "Zapisz pomysł: nowa aplikacja do śledzenia nawyków"\n'
            '📧 "Sprawdź moje emaile"\n'
            '✅ "Dodaj zadanie: kupić mleko, jutro"\n'
            '📓 "Znajdź w Obsidian notatki o Pythonie"\n'
            '🎬 "Podsumuj ten film: https://youtube.com/..."\n\n'
            "Komendy:\n"
            "/notes [szukaj] - wyszukaj notatki\n"
            "/tasks - pokaż aktywne zadania\n"
            "/overdue - pokaż zaległe zadania\n"
            "/facts - co o Tobie wiem\n"
            "/clear - wyczyść kontekst rozmowy",
            parse_mode="Markdown",
        )

    async def notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notes command - quick note search."""
        if not self._is_authorized(update.effective_user.id):
            return

        query = " ".join(context.args) if context.args else ""
        response = await self.agent.process_message(
            update.effective_user.id,
            f"Pokaż moje notatki{f' szukając: {query}' if query else ''}",
        )
        await self._send_long_message(update, response)

    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command."""
        if not self._is_authorized(update.effective_user.id):
            return

        response = await self.agent.process_message(
            update.effective_user.id,
            "Pokaż moje aktywne zadania z Todoist",
        )
        await self._send_long_message(update, response)

    async def overdue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /overdue command."""
        if not self._is_authorized(update.effective_user.id):
            return

        response = await self.agent.process_message(
            update.effective_user.id,
            "Pokaż moje zaległe zadania",
        )
        await self._send_long_message(update, response)

    async def facts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /facts command."""
        if not self._is_authorized(update.effective_user.id):
            return

        user_id = update.effective_user.id
        facts = await self.agent.memory.get_facts(user_id)
        if not facts:
            await update.message.reply_text("🧠 Jeszcze nic o Tobie nie wiem. Pogadajmy!")
            return

        lines = ["🧠 Co o Tobie wiem:\n"]
        current_cat = ""
        for f in sorted(facts, key=lambda x: x["category"]):
            if f["category"] != current_cat:
                current_cat = f["category"]
                lines.append(f"\n**{current_cat.upper()}**")
            lines.append(f"  • {f['key']}: {f['value']}")

        await self._send_long_message(update, "\n".join(lines))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        user = update.effective_user
        if not self._is_authorized(user.id):
            await update.message.reply_text("⛔ Nie masz uprawnień.")
            return

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            response = await self.agent.process_message(user.id, update.message.text)
            await self._send_long_message(update, response)
        except Exception as e:
            logger.exception("Error processing message")
            await update.message.reply_text(f"❌ Przepraszam, wystąpił błąd: {e}")

    async def _send_long_message(self, update: Update, text: str, max_length: int = 4000):
        """Send long messages split into chunks if needed."""
        if len(text) <= max_length:
            await update.message.reply_text(text)
            return

        # Split on double newlines or single newlines
        chunks = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                chunks.append(current)
                current = line
            else:
                current += ("\n" if current else "") + line
        if current:
            chunks.append(current)

        for chunk in chunks:
            await update.message.reply_text(chunk)

    def build_application(self) -> Application:
        """Build and configure the Telegram bot application."""
        app = Application.builder().token(self.token).build()

        # Commands
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("notes", self.notes_command))
        app.add_handler(CommandHandler("tasks", self.tasks_command))
        app.add_handler(CommandHandler("overdue", self.overdue_command))
        app.add_handler(CommandHandler("facts", self.facts_command))

        # Regular messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        return app
