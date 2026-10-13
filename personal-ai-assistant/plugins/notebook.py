"""Smart Notebook Plugin - notes, tags, categories, priorities."""

from core.memory import Memory
from plugins.base import BasePlugin, PluginRegistry, ToolResult


class NotebookPlugin(BasePlugin):
    name = "notebook"

    def setup(self, memory: Memory, **kwargs):
        self.memory = memory

        self.registry.register_tool(
            name="create_note",
            description="Stwórz nową notatkę z tytułem, treścią, tagami i kategorią. Używaj do zapisywania pomysłów, przemyśleń i informacji.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Tytuł notatki"},
                    "content": {"type": "string", "description": "Treść notatki"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista tagów (np. ['pomysł', 'praca', 'pilne'])",
                    },
                    "category": {
                        "type": "string",
                        "description": "Kategoria: general, work, personal, ideas, projects, learning",
                        "enum": ["general", "work", "personal", "ideas", "projects", "learning"],
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priorytet 0-5 (5 = najwyższy)",
                        "minimum": 0,
                        "maximum": 5,
                    },
                },
                "required": ["title", "content"],
            },
            handler=self.create_note,
        )

        self.registry.register_tool(
            name="search_notes",
            description="Wyszukaj notatki po treści, kategorii lub tagu.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Fraza wyszukiwania (opcjonalnie)"},
                    "category": {"type": "string", "description": "Filtruj po kategorii"},
                    "tag": {"type": "string", "description": "Filtruj po tagu"},
                },
            },
            handler=self.search_notes,
        )

        self.registry.register_tool(
            name="update_note",
            description="Zaktualizuj istniejącą notatkę (tytuł, treść, tagi, kategorię lub priorytet).",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "ID notatki do aktualizacji"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "category": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 0, "maximum": 5},
                },
                "required": ["note_id"],
            },
            handler=self.update_note,
        )

        self.registry.register_tool(
            name="delete_note",
            description="Usuń notatkę po jej ID.",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "ID notatki do usunięcia"},
                },
                "required": ["note_id"],
            },
            handler=self.delete_note,
        )

    async def create_note(self, user_id: int, title: str, content: str, tags: list[str] | None = None, category: str = "general", priority: int = 0, **_) -> ToolResult:
        note_id = await self.memory.add_note(user_id, title, content, tags, category, priority)
        tags_str = ", ".join(tags) if tags else "brak"
        return ToolResult(
            content=f"✅ Notatka zapisana (ID: {note_id})\n"
            f"Tytuł: {title}\n"
            f"Kategoria: {category}\n"
            f"Tagi: {tags_str}\n"
            f"Priorytet: {priority}/5"
        )

    async def search_notes(self, user_id: int, query: str = "", category: str | None = None, tag: str | None = None, **_) -> ToolResult:
        notes = await self.memory.search_notes(user_id, query, category, tag)
        if not notes:
            return ToolResult(content="Nie znaleziono notatek pasujących do kryteriów.")

        lines = [f"Znaleziono {len(notes)} notatek:\n"]
        for n in notes:
            tags_str = ", ".join(n["tags"]) if n["tags"] else ""
            lines.append(
                f"[{n['id']}] {'⭐' * n['priority']} {n['title']}\n"
                f"   Kategoria: {n['category']} | Tagi: {tags_str}\n"
                f"   {n['content'][:100]}{'...' if len(n['content']) > 100 else ''}\n"
            )
        return ToolResult(content="\n".join(lines))

    async def update_note(self, user_id: int, note_id: int, **fields) -> ToolResult:
        fields.pop("user_id", None)
        await self.memory.update_note(note_id, **fields)
        return ToolResult(content=f"✅ Notatka {note_id} zaktualizowana.")

    async def delete_note(self, user_id: int, note_id: int, **_) -> ToolResult:
        await self.memory.delete_note(note_id)
        return ToolResult(content=f"🗑️ Notatka {note_id} usunięta.")
