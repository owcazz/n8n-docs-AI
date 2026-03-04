"""Task Manager Plugin - Todoist integration for task tracking."""

import logging
from datetime import datetime, timezone

from plugins.base import BasePlugin, PluginRegistry, ToolResult

logger = logging.getLogger(__name__)


class TaskManagerPlugin(BasePlugin):
    name = "tasks"

    def setup(self, todoist_token: str = "", **kwargs):
        self.todoist_token = todoist_token
        self._api = None

        self.registry.register_tool(
            name="list_tasks",
            description="Pokaż listę aktywnych zadań z Todoist. Możesz filtrować po projekcie lub priorytecie.",
            parameters={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Nazwa projektu (opcjonalnie)"},
                    "priority": {
                        "type": "integer",
                        "description": "Filtruj po priorytecie 1-4 (4=najwyższy w Todoist)",
                        "minimum": 1,
                        "maximum": 4,
                    },
                },
            },
            handler=self.list_tasks,
        )

        self.registry.register_tool(
            name="add_task",
            description="Dodaj nowe zadanie do Todoist z opcjonalnym terminem i priorytetem.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Treść zadania"},
                    "description": {"type": "string", "description": "Opis szczegółowy (opcjonalnie)"},
                    "due_string": {
                        "type": "string",
                        "description": "Termin w języku naturalnym (np. 'jutro', 'za tydzień', 'piątek o 15:00')",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priorytet 1-4 (4=najwyższy)",
                        "default": 1,
                    },
                    "project_name": {"type": "string", "description": "Nazwa projektu (opcjonalnie)"},
                },
                "required": ["content"],
            },
            handler=self.add_task,
        )

        self.registry.register_tool(
            name="complete_task",
            description="Oznacz zadanie jako ukończone w Todoist.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "ID zadania do zamknięcia"},
                },
                "required": ["task_id"],
            },
            handler=self.complete_task,
        )

        self.registry.register_tool(
            name="get_overdue_tasks",
            description="Pokaż zaległe zadania (po terminie).",
            parameters={"type": "object", "properties": {}},
            handler=self.get_overdue_tasks,
        )

    def _get_api(self):
        if not self._api:
            if not self.todoist_token:
                raise RuntimeError("Todoist nie jest skonfigurowany. Ustaw TODOIST_API_TOKEN w .env")
            from todoist_api_python.api import TodoistAPI
            self._api = TodoistAPI(self.todoist_token)
        return self._api

    async def list_tasks(self, user_id: int, project_name: str | None = None, priority: int | None = None, **_) -> ToolResult:
        try:
            api = self._get_api()
            tasks = api.get_tasks()

            if project_name:
                projects = api.get_projects()
                project_id = None
                for p in projects:
                    if p.name.lower() == project_name.lower():
                        project_id = p.id
                        break
                if project_id:
                    tasks = [t for t in tasks if t.project_id == project_id]

            if priority:
                tasks = [t for t in tasks if t.priority == priority]

            if not tasks:
                return ToolResult(content="Brak zadań spełniających kryteria.")

            priority_icons = {1: "⬜", 2: "🟦", 3: "🟧", 4: "🟥"}
            lines = [f"📋 Znaleziono {len(tasks)} zadań:\n"]
            for t in tasks:
                icon = priority_icons.get(t.priority, "⬜")
                due_str = ""
                if t.due:
                    due_str = f" | 📅 {t.due.string}"
                lines.append(f"{icon} [{t.id}] {t.content}{due_str}")
                if t.description:
                    lines.append(f"   {t.description[:80]}")

            return ToolResult(content="\n".join(lines))
        except Exception as e:
            return ToolResult(content=f"Błąd Todoist: {e}", is_error=True)

    async def add_task(self, user_id: int, content: str, description: str = "", due_string: str | None = None, priority: int = 1, project_name: str | None = None, **_) -> ToolResult:
        try:
            api = self._get_api()
            kwargs = {"content": content, "priority": priority}
            if description:
                kwargs["description"] = description
            if due_string:
                kwargs["due_string"] = due_string
                kwargs["due_lang"] = "pl"

            if project_name:
                projects = api.get_projects()
                for p in projects:
                    if p.name.lower() == project_name.lower():
                        kwargs["project_id"] = p.id
                        break

            task = api.add_task(**kwargs)
            due_info = f"\nTermin: {task.due.string}" if task.due else ""
            return ToolResult(
                content=f"✅ Zadanie dodane (ID: {task.id})\n"
                f"Treść: {task.content}{due_info}\n"
                f"Priorytet: {priority}/4"
            )
        except Exception as e:
            return ToolResult(content=f"Błąd dodawania zadania: {e}", is_error=True)

    async def complete_task(self, user_id: int, task_id: str, **_) -> ToolResult:
        try:
            api = self._get_api()
            api.close_task(task_id)
            return ToolResult(content=f"✅ Zadanie {task_id} oznaczone jako ukończone!")
        except Exception as e:
            return ToolResult(content=f"Błąd zamykania zadania: {e}", is_error=True)

    async def get_overdue_tasks(self, user_id: int, **_) -> ToolResult:
        try:
            api = self._get_api()
            tasks = api.get_tasks(filter="overdue")
            if not tasks:
                return ToolResult(content="🎉 Brak zaległych zadań! Wszystko na bieżąco.")

            lines = [f"⚠️ Masz {len(tasks)} zaległych zadań:\n"]
            for t in tasks:
                due_str = t.due.string if t.due else "brak terminu"
                lines.append(f"🟥 [{t.id}] {t.content} (termin: {due_str})")

            return ToolResult(content="\n".join(lines))
        except Exception as e:
            return ToolResult(content=f"Błąd Todoist: {e}", is_error=True)
