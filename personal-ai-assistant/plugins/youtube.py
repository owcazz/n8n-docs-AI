"""YouTube Analyzer Plugin - fetch video info, transcripts, and generate summaries."""

import logging
import re

from plugins.base import BasePlugin, PluginRegistry, ToolResult

logger = logging.getLogger(__name__)


def _extract_video_id(url_or_id: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


class YouTubePlugin(BasePlugin):
    name = "youtube"

    def setup(self, **kwargs):
        self.registry.register_tool(
            name="youtube_info",
            description="Pobierz informacje o filmie YouTube (tytuł, opis, długość, kanał).",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Link YouTube lub ID filmu"},
                },
                "required": ["url"],
            },
            handler=self.get_video_info,
        )

        self.registry.register_tool(
            name="youtube_transcript",
            description="Pobierz transkrypcję/napisy filmu YouTube. Używaj do analizy treści wideo.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Link YouTube lub ID filmu"},
                    "language": {
                        "type": "string",
                        "description": "Kod języka (np. 'pl', 'en'). Domyślnie szuka polskich, potem angielskich.",
                        "default": "pl",
                    },
                },
                "required": ["url"],
            },
            handler=self.get_transcript,
        )

        self.registry.register_tool(
            name="youtube_summary",
            description="Pobierz transkrypcję i przygotuj kluczowe punkty filmu YouTube do podsumowania.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Link YouTube lub ID filmu"},
                },
                "required": ["url"],
            },
            handler=self.get_summary_data,
        )

    async def get_video_info(self, user_id: int, url: str, **_) -> ToolResult:
        video_id = _extract_video_id(url)
        if not video_id:
            return ToolResult(content="Nie udało się rozpoznać linku YouTube.", is_error=True)

        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

            duration_min = info.get("duration", 0) // 60
            duration_sec = info.get("duration", 0) % 60

            return ToolResult(
                content=f"🎬 Informacje o filmie:\n\n"
                f"Tytuł: {info.get('title', '?')}\n"
                f"Kanał: {info.get('uploader', '?')}\n"
                f"Długość: {duration_min}:{duration_sec:02d}\n"
                f"Wyświetlenia: {info.get('view_count', '?'):,}\n"
                f"Polubienia: {info.get('like_count', '?')}\n"
                f"Data: {info.get('upload_date', '?')}\n"
                f"Opis:\n{(info.get('description', '') or '')[:500]}"
            )
        except Exception as e:
            return ToolResult(content=f"Błąd pobierania informacji: {e}", is_error=True)

    async def get_transcript(self, user_id: int, url: str, language: str = "pl", **_) -> ToolResult:
        video_id = _extract_video_id(url)
        if not video_id:
            return ToolResult(content="Nie udało się rozpoznać linku YouTube.", is_error=True)

        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Try requested language, then fallback
            transcript = None
            for lang in [language, "en", "auto"]:
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    try:
                        transcript = transcript_list.find_transcript([lang]).fetch()
                    except Exception:
                        # Try generated/auto transcripts
                        for t in transcript_list:
                            transcript = t.fetch()
                            break
                    if transcript:
                        break
                except Exception:
                    continue

            if not transcript:
                return ToolResult(content="Brak dostępnych napisów dla tego filmu.", is_error=True)

            # Format transcript with timestamps
            lines = []
            for entry in transcript:
                minutes = int(entry["start"]) // 60
                seconds = int(entry["start"]) % 60
                lines.append(f"[{minutes:02d}:{seconds:02d}] {entry['text']}")

            full_text = "\n".join(lines)
            # Truncate if too long
            if len(full_text) > 8000:
                full_text = full_text[:8000] + "\n\n... [transkrypcja skrócona]"

            return ToolResult(content=f"📝 Transkrypcja:\n\n{full_text}")
        except Exception as e:
            return ToolResult(content=f"Błąd pobierania transkrypcji: {e}", is_error=True)

    async def get_summary_data(self, user_id: int, url: str, **_) -> ToolResult:
        """Fetch both info and transcript for AI to summarize."""
        info_result = await self.get_video_info(user_id, url)
        transcript_result = await self.get_transcript(user_id, url)

        if info_result.is_error and transcript_result.is_error:
            return ToolResult(content="Nie udało się pobrać danych o filmie.", is_error=True)

        combined = info_result.content + "\n\n" + transcript_result.content
        return ToolResult(
            content=f"Dane do podsumowania filmu:\n\n{combined}\n\n"
            "Proszę stwórz zwięzłe podsumowanie kluczowych punktów tego filmu."
        )
