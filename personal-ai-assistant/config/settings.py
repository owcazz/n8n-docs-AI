"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Claude API
    anthropic_api_key: str = Field(description="Anthropic API key")

    # Telegram
    telegram_bot_token: str = Field(description="Telegram Bot token from @BotFather")
    telegram_allowed_users: list[int] = Field(
        default_factory=list,
        description="Comma-separated list of allowed Telegram user IDs",
    )

    # Email (Gmail)
    gmail_credentials_path: str = Field(default="config/gmail_credentials.json")
    gmail_token_path: str = Field(default="config/gmail_token.json")

    # Todoist
    todoist_api_token: str = Field(default="")

    # Obsidian
    obsidian_vault_path: str = Field(default="")

    # General
    database_path: str = Field(default="data/assistant.db")
    log_level: str = Field(default="INFO")
    language: str = Field(default="pl")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
