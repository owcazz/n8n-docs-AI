"""Obsidian Integration Plugin - read, create, search and link notes in Obsidian vault."""

import logging
import re
from pathlib import Path

import frontmatter

from plugins.base import BasePlugin, PluginRegistry, ToolResult

logger = logging.getLogger(__name__)


class ObsidianPlugin(BasePlugin):
    name = "obsidian"

    def setup(self, vault_path: str = "", **kwargs):
        self.vault_path = Path(vault_path) if vault_path else None

        self.registry.register_tool(
            name="obsidian_search",
            description="Wyszukaj notatki w Obsidian vault po frazie w nazwie pliku lub treści.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Fraza do wyszukania"},
                    "search_content": {
                        "type": "boolean",
                        "description": "Szukaj także w treści notatek (wolniejsze)",
                        "default": False,
                    },
                },
                "required": ["query"],
            },
            handler=self.search_notes,
        )

        self.registry.register_tool(
            name="obsidian_read",
            description="Odczytaj pełną treść notatki Obsidian po ścieżce względnej.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ścieżka do notatki (np. 'Projects/MojProjekt.md')"},
                },
                "required": ["path"],
            },
            handler=self.read_note,
        )

        self.registry.register_tool(
            name="obsidian_create",
            description="Stwórz nową notatkę w Obsidian vault z opcjonalnym frontmatter YAML.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ścieżka notatki (np. 'Ideas/Nowy pomysł.md')"},
                    "content": {"type": "string", "description": "Treść notatki w Markdown"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tagi YAML frontmatter",
                    },
                },
                "required": ["path", "content"],
            },
            handler=self.create_note,
        )

        self.registry.register_tool(
            name="obsidian_append",
            description="Dopisz treść na końcu istniejącej notatki Obsidian.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ścieżka do notatki"},
                    "content": {"type": "string", "description": "Treść do dopisania"},
                },
                "required": ["path", "content"],
            },
            handler=self.append_to_note,
        )

        self.registry.register_tool(
            name="obsidian_list_folder",
            description="Pokaż listę notatek w folderze Obsidian vault.",
            parameters={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Ścieżka folderu (np. 'Projects/' lub '' dla roota)",
                        "default": "",
                    },
                },
            },
            handler=self.list_folder,
        )

    def _check_vault(self) -> str | None:
        if not self.vault_path or not self.vault_path.exists():
            return "Obsidian vault nie jest skonfigurowany. Ustaw OBSIDIAN_VAULT_PATH w .env"
        return None

    async def search_notes(self, user_id: int, query: str, search_content: bool = False, **_) -> ToolResult:
        if err := self._check_vault():
            return ToolResult(content=err, is_error=True)

        results = []
        query_lower = query.lower()

        for md_file in self.vault_path.rglob("*.md"):
            rel_path = md_file.relative_to(self.vault_path)
            # Skip hidden folders
            if any(part.startswith(".") for part in rel_path.parts):
                continue

            if query_lower in md_file.stem.lower():
                results.append((str(rel_path), "nazwa pliku"))
            elif search_content:
                try:
                    text = md_file.read_text(encoding="utf-8")
                    if query_lower in text.lower():
                        # Find context around match
                        idx = text.lower().index(query_lower)
                        start = max(0, idx - 50)
                        end = min(len(text), idx + len(query) + 50)
                        snippet = text[start:end].replace("\n", " ")
                        results.append((str(rel_path), f"...{snippet}..."))
                except Exception:
                    continue

            if len(results) >= 30:
                break

        if not results:
            return ToolResult(content=f"Nie znaleziono notatek pasujących do '{query}'.")

        lines = [f"🔍 Znaleziono {len(results)} wyników dla '{query}':\n"]
        for path, context in results:
            lines.append(f"  📄 {path} ({context})")
        return ToolResult(content="\n".join(lines))

    async def read_note(self, user_id: int, path: str, **_) -> ToolResult:
        if err := self._check_vault():
            return ToolResult(content=err, is_error=True)

        file_path = self.vault_path / path
        if not file_path.exists():
            return ToolResult(content=f"Notatka nie istnieje: {path}", is_error=True)

        try:
            post = frontmatter.load(str(file_path))
            meta_lines = []
            if post.metadata:
                meta_lines.append("--- Metadane ---")
                for k, v in post.metadata.items():
                    meta_lines.append(f"{k}: {v}")
                meta_lines.append("---\n")

            content = "\n".join(meta_lines) + post.content

            # Extract wikilinks
            links = re.findall(r"\[\[([^\]]+)\]\]", post.content)
            if links:
                content += f"\n\n🔗 Linki: {', '.join(links)}"

            return ToolResult(content=f"📄 {path}\n\n{content[:4000]}")
        except Exception as e:
            return ToolResult(content=f"Błąd odczytu notatki: {e}", is_error=True)

    async def create_note(self, user_id: int, path: str, content: str, tags: list[str] | None = None, **_) -> ToolResult:
        if err := self._check_vault():
            return ToolResult(content=err, is_error=True)

        file_path = self.vault_path / path
        if file_path.exists():
            return ToolResult(content=f"Notatka już istnieje: {path}. Użyj obsidian_append aby dopisać.", is_error=True)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        post = frontmatter.Post(content)
        if tags:
            post["tags"] = tags
        post["created"] = "{{date}}"

        file_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return ToolResult(content=f"✅ Notatka utworzona: {path}")

    async def append_to_note(self, user_id: int, path: str, content: str, **_) -> ToolResult:
        if err := self._check_vault():
            return ToolResult(content=err, is_error=True)

        file_path = self.vault_path / path
        if not file_path.exists():
            return ToolResult(content=f"Notatka nie istnieje: {path}", is_error=True)

        existing = file_path.read_text(encoding="utf-8")
        file_path.write_text(existing + "\n\n" + content, encoding="utf-8")
        return ToolResult(content=f"✅ Dopisano do notatki: {path}")

    async def list_folder(self, user_id: int, folder: str = "", **_) -> ToolResult:
        if err := self._check_vault():
            return ToolResult(content=err, is_error=True)

        target = self.vault_path / folder
        if not target.exists():
            return ToolResult(content=f"Folder nie istnieje: {folder}", is_error=True)

        items = []
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                count = sum(1 for _ in item.rglob("*.md"))
                items.append(f"📁 {item.name}/ ({count} notatek)")
            elif item.suffix == ".md":
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} B)")

        if not items:
            return ToolResult(content=f"Folder '{folder}' jest pusty.")

        return ToolResult(content=f"📂 {folder or '/'}\n\n" + "\n".join(items))
