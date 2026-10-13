"""Core AI Agent - the brain that orchestrates all plugins."""

import json
import logging
from typing import Any

import anthropic

from core.memory import Memory
from plugins.base import PluginRegistry, ToolResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś zaawansowanym osobistym asystentem AI o imieniu PAI (Personal AI).
Twoje główne cechy:
- Mówisz po polsku (chyba że użytkownik pisze w innym języku)
- Jesteś proaktywny - dopytaj o szczegóły, proponuj rozwiązania
- Masz dostęp do notatnika, emaili, zadań, Obsidian i analizy YouTube
- Pamiętasz kontekst z poprzednich rozmów
- Jesteś konkretny i pomocny, unikasz zbędnego gadania

Masz dostęp do następujących narzędzi (tools), które możesz wywoływać:

{tools_description}

Gdy użytkownik pyta o coś, co wymaga narzędzia:
1. Wybierz odpowiednie narzędzie
2. Podaj wymagane parametry
3. Poczekaj na wynik i skomentuj go użytkownikowi

Bądź naturalny, pomocny i proaktywny. Jeśli widzisz okazję do usprawnienia,
zaproponuj to. Jeśli czegoś nie wiesz, powiedz wprost.

{context}
"""


class Agent:
    """Main AI agent that processes messages and dispatches to plugins."""

    def __init__(self, api_key: str, memory: Memory, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.memory = memory
        self.model = model
        self.registry = PluginRegistry()

    def get_tools_schema(self) -> list[dict]:
        """Get all registered tools in Anthropic API format."""
        tools = []
        for tool_name, tool_def in self.registry.tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_def["description"],
                "input_schema": tool_def["parameters"],
            })
        return tools

    def get_tools_description(self) -> str:
        """Human-readable description of available tools."""
        lines = []
        for name, tool_def in self.registry.tools.items():
            lines.append(f"- **{name}**: {tool_def['description']}")
        return "\n".join(lines)

    async def process_message(self, user_id: int, message: str) -> str:
        """Process a user message through the agent pipeline."""
        # Store user message
        await self.memory.add_message(user_id, "user", message)

        # Build context from memory
        context = await self.memory.build_context(user_id)
        context_block = f"\n=== Kontekst użytkownika ===\n{context}" if context else ""

        # Get conversation history
        history = await self.memory.get_recent_messages(user_id, limit=20)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]

        # Build system prompt
        system = SYSTEM_PROMPT.format(
            tools_description=self.get_tools_description(),
            context=context_block,
        )

        tools = self.get_tools_schema()

        # Run agent loop (tool use can be iterative)
        response_text = await self._agent_loop(system, messages, tools, user_id)

        # Store assistant response
        await self.memory.add_message(user_id, "assistant", response_text)

        # Extract and store any new facts the AI discovered
        await self._extract_facts(user_id, message, response_text)

        return response_text

    async def _agent_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        user_id: int,
        max_iterations: int = 10,
    ) -> str:
        """Run the agent loop, handling tool calls iteratively."""
        for _ in range(max_iterations):
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = await self.client.messages.create(**kwargs)

            # Collect text blocks
            text_parts = []
            tool_uses = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # If no tool calls, we're done
            if not tool_uses:
                return "\n".join(text_parts)

            # Process tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tool_use in tool_uses:
                result = await self._execute_tool(user_id, tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result.to_api_format(),
                    "is_error": result.is_error,
                })
                logger.info("Tool %s -> %s", tool_use.name, "error" if result.is_error else "ok")

            messages.append({"role": "user", "content": tool_results})

        return "\n".join(text_parts) if text_parts else "Przepraszam, przekroczono limit iteracji."

    async def _execute_tool(self, user_id: int, tool_name: str, tool_input: dict) -> ToolResult:
        """Execute a registered tool."""
        handler = self.registry.get_handler(tool_name)
        if not handler:
            return ToolResult(content=f"Nieznane narzędzie: {tool_name}", is_error=True)
        try:
            return await handler(user_id=user_id, **tool_input)
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return ToolResult(content=f"Błąd narzędzia {tool_name}: {e}", is_error=True)

    async def _extract_facts(self, user_id: int, user_msg: str, assistant_msg: str):
        """Use a lightweight call to extract any new facts from the conversation."""
        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                system=(
                    "Extract any new personal facts about the user from this exchange. "
                    "Return JSON array of objects with keys: category, key, value. "
                    "Categories: preferences, personal, work, habits, goals. "
                    "Return empty array [] if no new facts. Only return the JSON array, nothing else."
                ),
                messages=[
                    {"role": "user", "content": f"User: {user_msg}\nAssistant: {assistant_msg}"}
                ],
            )
            text = response.content[0].text.strip()
            facts = json.loads(text)
            for fact in facts:
                await self.memory.store_fact(
                    user_id,
                    fact["category"],
                    fact["key"],
                    fact["value"],
                )
        except Exception:
            # Non-critical - just log and continue
            logger.debug("Fact extraction skipped", exc_info=True)
