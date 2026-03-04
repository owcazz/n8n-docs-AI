"""Tests for the memory system."""

import pytest
import tempfile
import os

from core.memory import Memory


@pytest.fixture
async def memory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    mem = Memory(db_path)
    await mem.initialize()
    yield mem
    await mem.close()
    os.unlink(db_path)


async def test_add_and_get_messages(memory: Memory):
    await memory.add_message(1, "user", "Hello")
    await memory.add_message(1, "assistant", "Hi there!")

    messages = await memory.get_recent_messages(1)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_store_and_get_facts(memory: Memory):
    await memory.store_fact(1, "preferences", "language", "Polish")
    await memory.store_fact(1, "personal", "name", "Jan")

    all_facts = await memory.get_facts(1)
    assert len(all_facts) == 2

    pref_facts = await memory.get_facts(1, category="preferences")
    assert len(pref_facts) == 1
    assert pref_facts[0]["value"] == "Polish"


async def test_fact_upsert(memory: Memory):
    await memory.store_fact(1, "preferences", "color", "blue")
    await memory.store_fact(1, "preferences", "color", "green")

    facts = await memory.get_facts(1, category="preferences")
    assert len(facts) == 1
    assert facts[0]["value"] == "green"


async def test_notes_crud(memory: Memory):
    # Create
    note_id = await memory.add_note(1, "Test Note", "Content here", ["test", "demo"], "work", 3)
    assert note_id > 0

    # Search
    notes = await memory.search_notes(1)
    assert len(notes) == 1
    assert notes[0]["title"] == "Test Note"
    assert "test" in notes[0]["tags"]

    # Search by query
    notes = await memory.search_notes(1, query="Content")
    assert len(notes) == 1

    # Search by category
    notes = await memory.search_notes(1, category="work")
    assert len(notes) == 1
    notes = await memory.search_notes(1, category="personal")
    assert len(notes) == 0

    # Search by tag
    notes = await memory.search_notes(1, tag="test")
    assert len(notes) == 1

    # Update
    await memory.update_note(note_id, title="Updated Title")
    notes = await memory.search_notes(1)
    assert notes[0]["title"] == "Updated Title"

    # Delete
    await memory.delete_note(note_id)
    notes = await memory.search_notes(1)
    assert len(notes) == 0


async def test_build_context(memory: Memory):
    await memory.store_fact(1, "personal", "name", "Jan")
    await memory.add_note(1, "My Idea", "Great idea here", ["idea"], "ideas", 5)

    context = await memory.build_context(1)
    assert "Jan" in context
    assert "My Idea" in context


async def test_message_isolation_between_users(memory: Memory):
    await memory.add_message(1, "user", "User 1 message")
    await memory.add_message(2, "user", "User 2 message")

    msgs_1 = await memory.get_recent_messages(1)
    msgs_2 = await memory.get_recent_messages(2)

    assert len(msgs_1) == 1
    assert len(msgs_2) == 1
    assert msgs_1[0]["content"] == "User 1 message"
    assert msgs_2[0]["content"] == "User 2 message"
