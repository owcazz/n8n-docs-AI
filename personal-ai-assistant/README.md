# PAI - Personal AI Assistant

Zaawansowany osobisty asystent AI dostepny przez Telegram i CLI.
Twoj "drugi mozg" w kieszeni - zarzadza notatkami, emailami, zadaniami i analizuje tresc.

## Architektura

```
┌─────────────────────────────────────────┐
│           Telegram / CLI                │
│         (Interfejs uzytkownika)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Agent (core/agent.py)          │
│   Claude API + Tool Use + Memory        │
│   - Agent loop z iteracyjnym tool use   │
│   - Automatyczna ekstrakcja faktow      │
│   - Kontekst z pamieci dlugookresowej   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        Plugin Registry (tools)          │
├─────────┬────────┬────────┬─────┬───────┤
│Notebook │ Email  │ Tasks  │Obsi-│YouTube│
│  Plugin │Manager │Manager │dian │Analyz.│
│         │(Gmail) │(Todoi.)│     │       │
└─────────┴────────┴────────┴─────┴───────┘
               │
┌──────────────▼──────────────────────────┐
│     Memory (SQLite + aiosqlite)         │
│  - Conversations (historia rozmow)      │
│  - Facts (dlugoterm. wiedza o uzytkown.)│
│  - Notes (notatnik inteligentny)        │
└─────────────────────────────────────────┘
```

## Funkcje

### Notatnik inteligentny
- Tworzenie notatek z tagami, kategoriami i priorytetami
- Wyszukiwanie pelnotekstowe
- Automatyczne tagowanie i organizacja

### Zarzadzanie emailami (Gmail)
- Odczyt skrzynki z filtrami
- Czytanie pelnej tresci emaili
- Wysylanie i odpowiadanie na wiadomosci

### Kontrola zadan (Todoist)
- Lista aktywnych zadan
- Dodawanie nowych z terminem i priorytetem
- Sledzenie zaleglych zadan
- Oznaczanie ukonczonych

### Integracja Obsidian
- Przeszukiwanie vault po nazwie i tresci
- Czytanie notatek z metadanymi YAML
- Tworzenie nowych notatek
- Dopisywanie do istniejacych
- Przegladanie struktury folderow

### Analiza YouTube
- Pobieranie info o filmie (tytul, kanal, dlugosc)
- Pobieranie transkrypcji z timestampami
- Przygotowanie danych do podsumowania

### Pamiec persistentna
- Historia rozmow per uzytkownik
- Automatyczna ekstrakcja faktow (preferencje, dane osobowe, cele)
- Budowanie kontekstu z dlugookresowej pamieci

## Szybki start

### 1. Konfiguracja

```bash
cd personal-ai-assistant
cp .env.example .env
# Edytuj .env - uzupelnij klucze API
```

Wymagane minimum:
- `ANTHROPIC_API_KEY` - klucz API Claude
- `TELEGRAM_BOT_TOKEN` - token z @BotFather

Opcjonalnie:
- `TODOIST_API_TOKEN` - integracja z Todoist
- `GMAIL_CREDENTIALS_PATH` - integracja z Gmail (OAuth2)
- `OBSIDIAN_VAULT_PATH` - sciezka do vault Obsidian

### 2. Instalacja

```bash
# Opcja A: pip
pip install -e .

# Opcja B: Docker
docker compose up -d
```

### 3. Uruchomienie

```bash
# Tryb Telegram (produkcja)
python -m core.main

# Tryb CLI (testowanie lokalne)
python -m core.cli
```

### 4. Telegram - stworzenie bota

1. Napisz do @BotFather na Telegram
2. `/newbot` -> podaj nazwe
3. Skopiuj token do `.env`
4. Opcjonalnie: dodaj swoje user ID do `TELEGRAM_ALLOWED_USERS`
   (znajdziesz przez @userinfobot)

## Komendy Telegram

| Komenda | Opis |
|---------|------|
| `/start` | Powitanie i instrukcja |
| `/help` | Pomoc |
| `/notes [szukaj]` | Przeszukaj notatki |
| `/tasks` | Pokaz zadania Todoist |
| `/overdue` | Pokaz zalegle zadania |
| `/facts` | Co bot o Tobie wie |

## Przykladowe uzycie

```
Ty: Zapisz pomysl na aplikacje do sledzenia nawykow z AI
PAI: Notatka zapisana! Tagi: #pomysl #aplikacja #AI. Chcesz rozwinac ten pomysl?

Ty: Sprawdz moje emaile - sa jakies pilne?
PAI: Masz 3 nieprzeczytane wiadomosci. Najwazniejsza: od szefa...

Ty: Dodaj zadanie: przygotowac prezentacje na piatek, priorytet wysoki
PAI: Zadanie dodane do Todoist! Termin: piatek, priorytet 4/4.

Ty: Podsumuj ten film: https://youtube.com/watch?v=...
PAI: Film "Tytul" (15:30) - kluczowe punkty: 1. ... 2. ... 3. ...

Ty: Znajdz w Obsidian notatki o machine learning
PAI: Znaleziono 5 notatek: ...
```

## Rozwoj

```bash
# Instalacja z dev dependencies
pip install -e ".[dev]"

# Testy
pytest

# Linting
ruff check .

# Type checking
mypy .
```

### Dodawanie nowego pluginu

1. Stworz plik w `plugins/`
2. Dziedzicz z `BasePlugin`
3. Zarejestruj narzedzia w `setup()`
4. Dodaj plugin w `core/main.py`

```python
from plugins.base import BasePlugin, ToolResult

class MyPlugin(BasePlugin):
    name = "my_plugin"

    def setup(self, **kwargs):
        self.registry.register_tool(
            name="my_tool",
            description="Opis narzedzia",
            parameters={"type": "object", "properties": {...}},
            handler=self.my_handler,
        )

    async def my_handler(self, user_id: int, **kwargs) -> ToolResult:
        return ToolResult(content="Wynik")
```

## Licencja

MIT
