"""Human slash command for exact-content saves, not a model tool."""

from kohakuterrarium.modules.user_command.base import (
    BaseUserCommand,
    CommandLayer,
    UserCommandContext,
    UserCommandResult,
)

from .binding import binding
from .memory import MemoryService, MemoryUnavailable


class MemcodeSaveCommand(BaseUserCommand):
    name = "memcode-save"
    description = "Save the exact fact you type to your configured MemCode space"
    layer = CommandLayer.INPUT

    def __init__(self, memory: MemoryService | None = None):
        self._memory = memory

    async def _execute(
        self, args: str, context: UserCommandContext
    ) -> UserCommandResult:
        # Entering this human command approves exactly args. No boolean from an LLM is used.
        try:
            async with binding(self._memory) as memory:
                receipt = await memory.save_approved_fact(args)
            return UserCommandResult(
                output=f"Memory ingestion {receipt.id}: {receipt.status}. "
                "Queued facts become searchable after ingestion completes."
            )
        except ValueError:
            return UserCommandResult(
                error="Configure memory and type an approved fact (1 to 16000 characters)"
            )
        except MemoryUnavailable:
            return UserCommandResult(error="Memory save is temporarily unavailable")
