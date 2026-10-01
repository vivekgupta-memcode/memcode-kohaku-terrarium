"""Operator-controlled binding for an isolated single-user deployment."""

import os
from contextlib import asynccontextmanager

from memcode_sdk import AsyncMemcodeV2Client

from .memory import MemoryService


@asynccontextmanager
async def binding(injected: MemoryService | None):
    if injected is not None:
        yield injected
        return
    names = (
        "MEMCODE_API_KEY",
        "MEMCODE_SPACE_ID",
        "MEMCODE_USER_ID",
        "MEMCODE_ACTOR_ID",
    )
    values = [os.environ.get(name, "") for name in names]
    if any(not value.strip() for value in values):
        raise ValueError(
            "Configure the single-user MemCode binding in the host environment"
        )
    client = AsyncMemcodeV2Client(
        api_url="https://memory.memcode.in", api_key=values[0], timeout=2
    )
    try:
        yield MemoryService(client, values[1], values[2], values[3], timeout=2)
    finally:
        await client.close()
