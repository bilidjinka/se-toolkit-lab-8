# Plan and Scaffold

Before writing any feature code, you need a solid project structure and a plan. A well-scaffolded project makes everything easier: adding commands, testing, deploying. A bad structure means fighting the code at every step.

In this task, you use your coding agent to create a development plan and project skeleton.

## Requirements targeted

- **P0.1** Testable handler architecture — handlers work without Telegram
- **P0.2** CLI test mode: `cd bot && uv run bot.py --test "/command"` prints response to stdout

## What you will build

A `bot/` directory inside your repo with an entry point, handler layer, configuration, dependencies, and a `--test` mode for offline verification.

```
se-toolkit-lab-7/
├── bot/                    ← NEW
│   ├── bot.py              ← entry point (Telegram startup + --test mode)
│   ├── handlers/           ← command handlers (no Telegram dependency)
│   ├── services/           ← API client, LLM client
│   ├── config.py           ← env var loading
│   ├── pyproject.toml    ← bot dependencies
│   └── PLAN.md             ← development plan
├── backend/                ← existing
├── frontend/               ← existing
└── docker-compose.yml      ← existing
```

The key idea is **testable handlers**: your command logic is just functions that take input and return text. They don't know about Telegram. The `--test` flag calls them directly, and later the Telegram bot calls the same functions. Same logic, different entry points.

## Test mode

The autochecker verifies the bot via `--test` — no Telegram connection needed:

```terminal
cd bot
uv run bot.py --test "/start"                    # → prints welcome message
uv run bot.py --test "/help"                     # → prints command list
uv run bot.py --test "/health"                   # → prints backend status
uv run bot.py --test "/scores lab-04"
uv run bot.py --test "what labs are available"    # Task 3
```

- Prints response to **stdout**, exits with code **0**
- Reads config from `.env.bot.secret` (`LMS_API_URL`, `LMS_API_KEY`, `LLM_API_KEY`)
- Does **not** connect to Telegram (no `BOT_TOKEN` needed in test mode)

## Deliverables

### 1. Development plan (`bot/PLAN.md`)

A plan produced with your coding agent. Describe the approach for all tasks: scaffold, backend integration, intent routing, deployment. At least 100 words.

### 2. Bot entry point (`bot/bot.py`)

Ask your coding agent to create the entry point with `--test` mode support. Handlers can return placeholder text for now — real implementation comes in Task 2. Your job is to verify it works and understand the architecture (see [Test mode](#test-mode) above).

### 3. Handler directory (`bot/handlers/`)

Handler modules separated from the Telegram transport layer. The `--test` mode calls them directly without Telegram.

### 4. Dependencies (`bot/pyproject.toml`)

Bot-specific Python project with dependencies. `cd bot && uv sync` must work without errors. Do **not** create `requirements.txt` — use `pyproject.toml` and `uv` exclusively.

### 5. Environment files

`.env.bot.example` must include `BOT_TOKEN`, `LMS_API_URL`, `LMS_API_KEY` with placeholder values. On the VM, `.env.bot.secret` must exist with real values filled in.

## Verify

### Verify in test mode

Run on your VM:

```terminal
cd ~/se-toolkit-lab-7/bot
uv sync
uv run bot.py --test "/start"
```

You should see a welcome message printed to the terminal. If it prints something and exits with code 0 — the scaffold works.

Try the other commands too — they can return placeholder text for now, but they must not crash:

```terminal
uv run bot.py --test "/help"
uv run bot.py --test "/health"
uv run bot.py --test "/labs"
```

**What to check:**
- Each command prints *something* to stdout (even "Not implemented yet" is fine for this task)
- No Python tracebacks
- Exit code is 0 (the command doesn't show an error)

### Deploy and verify in Telegram

After verifying with `--test`, deploy the bot on your VM and check it responds in Telegram. You'll repeat this pattern after every task — it's how you know the bot works for real users, not just in test mode.

1. Push your changes and pull on the VM:

   ```terminal
   cd ~/se-toolkit-lab-7
   git pull
   cd bot && uv sync
   ```

2. Start the bot (kills any previous instance):

   ```terminal
   pkill -f "bot.py" 2>/dev/null; nohup uv run bot.py > bot.log 2>&1 &
   ```

3. Open Telegram and send `/start` to your bot. You should see the welcome message.

**If the bot doesn't respond in Telegram:**

1. Check the log: `tail -20 bot.log`
2. Common issues:
   - `BOT_TOKEN` is wrong or missing in `.env.bot.secret`
   - Another bot process is already running (check `ps aux | grep bot.py`)
   - `.env.bot.secret` doesn't exist (copy from `.env.bot.example`)

## Acceptance criteria

- [ ] `bot/PLAN.md` exists with at least 100 words.
- [ ] `bot/pyproject.toml` exists and `cd bot && uv sync` succeeds.
- [ ] `bot/handlers/` directory exists with at least one module.
- [ ] `cd bot && uv run bot.py --test "/start"` exits 0 with non-empty output.
- [ ] `.env.bot.secret` exists on the VM with `BOT_TOKEN`, `LMS_API_URL`, `LMS_API_KEY`.
- [ ] Bot responds to `/start` in Telegram.
- [ ] Repo is cloned at `~/se-toolkit-lab-7` on the VM.
- [ ] Git workflow followed (issue, branch, PR, review, merge).
