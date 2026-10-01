import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from kohakuterrarium.modules.user_command.base import UserCommandContext
from memcode_sdk import MemcodeSDKError

from memcode_kohaku_terrarium.commands import MemcodeSaveCommand
from memcode_kohaku_terrarium.memory import MemoryService, MemoryUnavailable
from memcode_kohaku_terrarium.tools import MemcodeRecallTool


def record(user, space, content):
    return SimpleNamespace(
        content=content, space=SimpleNamespace(id=space), metadata={"user_id": user}
    )


@pytest.fixture
def client():
    return SimpleNamespace(
        search=AsyncMock(
            return_value=SimpleNamespace(
                results=[
                    record("alice", "space-a", "Concise replies"),
                    record("bob", "space-a", "private-bob"),
                    record("alice", "space-b", "private-space"),
                ]
            )
        ),
        ingest=AsyncMock(return_value=SimpleNamespace(id="job-1", status="queued")),
    )


async def test_real_user_command_saves_exact_fact_and_later_tool_recalls_it(client):
    first = MemoryService(client, "space-a", "alice", "actor-a")
    command = MemcodeSaveCommand(first)
    result = await command.execute("Concise replies", UserCommandContext())
    assert result.success and "queued" in result.output
    request = client.ingest.call_args.kwargs
    assert request["content"] == "Concise replies"
    assert request["metadata"]["user_id"] == "alice"
    later = MemcodeRecallTool(
        memory=MemoryService(client, "space-a", "alice", "actor-a")
    )
    result = await later.execute({"query": "style"})
    assert result.success
    assert json.loads(result.output) == {"facts": ["Concise replies"]}
    assert client.search.call_args.kwargs["scope"] == "context_only"
    assert not client.search.call_args.kwargs["include_original_chunks"]
    assert client.ingest.call_count == 1


async def test_identity_arguments_and_blank_content_are_rejected_without_requests(
    client,
):
    memory = MemoryService(client, "s", "u", "a")
    tool = MemcodeRecallTool(memory=memory)
    result = await tool.execute({"query": "x", "user_id": "bob"})
    assert not result.success
    assert not (await tool.execute({"query": " "})).success
    assert not (
        await MemcodeSaveCommand(memory).execute(" ", UserCommandContext())
    ).success
    client.search.assert_not_called()
    client.ingest.assert_not_called()


async def test_provider_error_is_generic_in_real_framework_wrappers(client):
    client.search.side_effect = MemcodeSDKError("private-prompt synthetic-key")
    client.ingest.side_effect = MemcodeSDKError("private-prompt synthetic-key")
    memory = MemoryService(client, "s", "u", "a")
    for result in [
        await MemcodeRecallTool(memory=memory).execute({"query": "preferences"}),
        await MemcodeSaveCommand(memory).execute("approved", UserCommandContext()),
    ]:
        assert not result.success
        assert "private" not in result.error and "synthetic-key" not in result.error


async def test_write_keys_are_stable_and_users_are_separated(client):
    memory = MemoryService(client, "s", "alice", "a")
    await memory.save_approved_fact("approved")
    key = client.ingest.call_args.kwargs["idempotency_key"]
    await memory.save_approved_fact("approved")
    assert key == client.ingest.call_args.kwargs["idempotency_key"]
    await MemoryService(client, "s", "bob", "b").save_approved_fact("approved")
    assert key != client.ingest.call_args.kwargs["idempotency_key"]


async def test_timeout_cancels_service_work(client):
    cancelled = asyncio.Event()

    async def slow(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    client.search = slow
    with pytest.raises(MemoryUnavailable):
        await MemoryService(client, "s", "u", "a", timeout=0.01).recall("x")
    assert cancelled.is_set()


async def test_missing_environment_sends_no_request(monkeypatch):
    for name in [
        "MEMCODE_API_KEY",
        "MEMCODE_SPACE_ID",
        "MEMCODE_USER_ID",
        "MEMCODE_ACTOR_ID",
    ]:
        monkeypatch.delenv(name, raising=False)
    assert not (await MemcodeRecallTool().execute({"query": "preferences"})).success
    assert not (
        await MemcodeSaveCommand().execute("approved", UserCommandContext())
    ).success


def test_manifest_classes_load_without_credentials_or_network():
    import importlib
    from pathlib import Path

    import yaml

    manifest = yaml.safe_load(Path("kohaku.yaml").read_text())
    for entry in manifest["tools"] + manifest["user_commands"]:
        cls = getattr(importlib.import_module(entry["module"]), entry["class"])
        assert cls() is not None
