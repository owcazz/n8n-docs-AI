"""Email Manager Plugin - read, summarize, and reply to emails via Gmail API."""

import base64
import logging
from email.mime.text import MIMEText
from pathlib import Path

from plugins.base import BasePlugin, PluginRegistry, ToolResult

logger = logging.getLogger(__name__)


def _get_gmail_service(credentials_path: str, token_path: str):
    """Build Gmail API service (lazy import to avoid hard dependency)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    creds = None
    token_file = Path(token_path)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


class EmailPlugin(BasePlugin):
    name = "email"

    def setup(self, credentials_path: str = "", token_path: str = "", **kwargs):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None

        self.registry.register_tool(
            name="read_emails",
            description="Odczytaj ostatnie emaile ze skrzynki Gmail. Zwraca listę z nadawcą, tematem i fragmentem treści.",
            parameters={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Ile emaili odczytać (domyślnie 10)",
                        "default": 10,
                    },
                    "query": {
                        "type": "string",
                        "description": "Filtr wyszukiwania Gmail (np. 'is:unread', 'from:boss@company.com')",
                    },
                },
            },
            handler=self.read_emails,
        )

        self.registry.register_tool(
            name="read_email_detail",
            description="Odczytaj pełną treść konkretnego emaila po jego ID.",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {"type": "string", "description": "ID emaila do odczytania"},
                },
                "required": ["email_id"],
            },
            handler=self.read_email_detail,
        )

        self.registry.register_tool(
            name="send_email",
            description="Wyślij email przez Gmail. Możesz podać adresata, temat i treść.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Adres email odbiorcy"},
                    "subject": {"type": "string", "description": "Temat wiadomości"},
                    "body": {"type": "string", "description": "Treść wiadomości"},
                    "reply_to_id": {
                        "type": "string",
                        "description": "ID emaila, na który odpowiadamy (opcjonalnie)",
                    },
                },
                "required": ["to", "subject", "body"],
            },
            handler=self.send_email,
        )

    def _get_service(self):
        if not self._service:
            if not self.credentials_path:
                raise RuntimeError(
                    "Gmail nie jest skonfigurowany. Ustaw GMAIL_CREDENTIALS_PATH w .env"
                )
            self._service = _get_gmail_service(self.credentials_path, self.token_path)
        return self._service

    async def read_emails(self, user_id: int, max_results: int = 10, query: str = "is:inbox", **_) -> ToolResult:
        try:
            service = self._get_service()
            results = service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                return ToolResult(content="Skrzynka jest pusta (dla podanego filtra).")

            lines = [f"📬 Znaleziono {len(messages)} wiadomości:\n"]
            for msg_info in messages:
                msg = service.users().messages().get(
                    userId="me", id=msg_info["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()

                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                snippet = msg.get("snippet", "")[:120]
                is_unread = "UNREAD" in msg.get("labelIds", [])
                marker = "🔴 " if is_unread else "  "

                lines.append(
                    f"{marker}[{msg_info['id'][:8]}] Od: {headers.get('From', '?')}\n"
                    f"   Temat: {headers.get('Subject', '(brak)')}\n"
                    f"   Data: {headers.get('Date', '?')}\n"
                    f"   {snippet}...\n"
                )

            return ToolResult(content="\n".join(lines))
        except Exception as e:
            return ToolResult(content=f"Błąd odczytu emaili: {e}", is_error=True)

    async def read_email_detail(self, user_id: int, email_id: str, **_) -> ToolResult:
        try:
            service = self._get_service()
            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

            # Extract body
            body = ""
            payload = msg["payload"]
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
            elif "body" in payload and "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

            return ToolResult(
                content=f"📧 Email szczegóły:\n"
                f"Od: {headers.get('From', '?')}\n"
                f"Do: {headers.get('To', '?')}\n"
                f"Temat: {headers.get('Subject', '(brak)')}\n"
                f"Data: {headers.get('Date', '?')}\n"
                f"---\n{body[:3000]}"
            )
        except Exception as e:
            return ToolResult(content=f"Błąd odczytu emaila: {e}", is_error=True)

    async def send_email(self, user_id: int, to: str, subject: str, body: str, reply_to_id: str | None = None, **_) -> ToolResult:
        try:
            service = self._get_service()
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            send_body: dict = {"raw": raw}

            if reply_to_id:
                original = service.users().messages().get(
                    userId="me", id=reply_to_id, format="metadata",
                    metadataHeaders=["Message-ID"],
                ).execute()
                headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
                if "Message-ID" in headers:
                    message["In-Reply-To"] = headers["Message-ID"]
                    message["References"] = headers["Message-ID"]
                send_body["threadId"] = original.get("threadId")

            service.users().messages().send(userId="me", body=send_body).execute()
            return ToolResult(content=f"✅ Email wysłany do {to}\nTemat: {subject}")
        except Exception as e:
            return ToolResult(content=f"Błąd wysyłania emaila: {e}", is_error=True)
