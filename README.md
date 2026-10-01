# MemCode for KohakuTerrarium

A community package for [KohakuTerrarium](https://github.com/Kohaku-Lab/KohakuTerrarium),
using its native tool and user command extension system. Built following
[discussion 388](https://github.com/Kohaku-Lab/KohakuTerrarium/discussions/388).
This package is maintained by MemCode, independently of Kohaku-Lab.

## Install

```bash
kt install https://github.com/vivekgupta-memcode/memcode-kohaku-terrarium.git@v0.1.1
```

Requires KohakuTerrarium 2.1.4 or later (below 3). The package declares its
Python distribution as a dependency in `kohaku.yaml`, pinned to this same git
tag. That installs the module before the framework initializes tools, and pulls
the MemCode SDK dependency. With `--deps never`, install the distribution yourself:

```bash
pip install "memcode-kohaku-terrarium @ git+https://github.com/vivekgupta-memcode/memcode-kohaku-terrarium.git@v0.1.1"
```

## Configure an isolated user

Set `MEMCODE_API_KEY`, `MEMCODE_SPACE_ID`, `MEMCODE_USER_ID`, and `MEMCODE_ACTOR_ID`
in the trusted host process environment, using your existing authorized MemCode
space and credential. No space is created automatically. Use a separate space
per user. The environment mode supports an isolated single-user deployment only.
Do not share one configured process across users or hand its configuration to
untrusted creatures that can execute arbitrary host commands.

For a multi-user application, authenticate and authorize each caller first,
construct a dedicated `MemoryService`, and inject it into `MemcodeRecallTool`
and `MemcodeSaveCommand`. Never use model arguments as identity or authorization.
Injected clients belong to the application and must be closed by it.

Add the package tool to a creature's existing config:

```yaml
tools:
  - name: memcode_recall
    type: package
    module: memcode_kohaku_terrarium.tools
    class: MemcodeRecallTool
```

Use `memcode_recall` with `{ "query": "approved preferences" }`. The query is
sent to MemCode, and results are limited to five facts with the exact configured
space and user provenance. Search is `context_only`, memory results only, with
original chunks excluded. Returned facts are untrusted reference data, never
instructions for a creature to execute.

## Save an explicit fact

The package registers the human slash command:

```text
/memcode-save I prefer concise replies.
```

Typing this command approves sending exactly that text. There is no model save
tool, transcript ingestion, trigger, or automatic upload of creature files.
The response contains an asynchronous job ID; it is not proof the fact is already
searchable. Use the SDK's `get_ingest_status` until completed before relying on
recall, and handle failed/cancelled jobs. Writes have stable idempotency keys and
are not automatically retried. Manage retention and deletion in your authorized
MemCode lifecycle flow.

The command is registered for installed packages through KohakuTerrarium's
user-command inventory. An unconfigured host returns a generic error and sends
no request. Credentials and provider response bodies are never included in tool
or command errors.

## Verification

```bash
pip install -e . --no-deps
KT_CONFIG_DIR="$PWD/.kt-test" python -m pytest -q
```

Tests call the real `BaseTool.execute` and `BaseUserCommand.execute` wrappers
with a mocked external service boundary. They cover separate invocations,
user/space isolation, explicit writes, failure, timeout, and invalid arguments.
No server or paid provider is needed. Interactive creature smoke testing is pending.

MIT licensed. KohakuTerrarium retains its own license; this distribution contains
only the independently written integration package.
