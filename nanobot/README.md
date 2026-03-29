# Nanobot — LMS Agent

A nanobot-based agent that connects to the LMS backend via MCP (Model Context Protocol) and provides a web chat interface.

## What This Is

This project deploys a **nanobot agent** that:

- Connects to the **Qwen Code API** for LLM-powered responses
- Uses **MCP servers** to access live LMS backend data (labs, scores, pass rates)
- Exposes a **WebSocket channel** for web clients to interact with it
- Renders **structured UI messages** (choices, confirmations) in the web client
- Runs as a **Docker service** alongside the backend and other components

## Architecture

```text
browser -> caddy -> nanobot webchat channel -> nanobot gateway -> mcp_lms -> backend
nanobot gateway -> qwen-code-api -> Qwen
nanobot gateway -> mcp_webchat -> nanobot webchat UI relay -> browser
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `config.json` | Nanobot configuration (LLM provider, MCP servers, channels) |
| `entrypoint.py` | Runtime config resolver — injects env vars into config before starting gateway |
| `Dockerfile` | Multi-stage build using `uv` for dependency management |
| `workspace/` | Agent workspace containing skills and memory |
| `workspace/skills/lms/SKILL.md` | LMS-specific skill prompt teaching the agent how to use LMS tools |

## Project Structure

```
nanobot/
├── config.json           # Base configuration (committed, no secrets)
├── config.resolved.json  # Runtime-resolved config (generated, gitignored)
├── Dockerfile            # Container build instructions
├── entrypoint.py         # Config resolver + gateway launcher
├── pyproject.toml        # Python dependencies (uv)
├── uv.lock               # Locked dependency versions
└── workspace/
    ├── skills/
    │   ├── lms/
    │   │   └── SKILL.md  # LMS tool usage strategy
    │   └── structured-ui/
    │       └── SKILL.md  # Shared structured UI handling
    └── memory/
        └── HISTORY.md    # Conversation history
```

## Configuration

### Environment Variables

The following environment variables must be set (via `.env.docker.secret`):

| Variable | Purpose |
|----------|---------|
| `LLM_API_KEY` | Qwen Code API key |
| `LLM_API_BASE_URL` | Qwen API endpoint (`http://qwen-code-api:42005/v1`) |
| `LLM_API_MODEL` | Model name (`coder-model`) |
| `NANOBOT_GATEWAY_CONTAINER_ADDRESS` | Gateway host (`0.0.0.0`) |
| `NANOBOT_GATEWAY_CONTAINER_PORT` | Gateway port |
| `NANOBOT_LMS_BACKEND_URL` | LMS backend URL (`http://backend:42002`) |
| `NANOBOT_LMS_API_KEY` | LMS API key for backend access |
| `NANOBOT_WEBCHAT_CONTAINER_ADDRESS` | Webchat host (`0.0.0.0`) |
| `NANOBOT_WEBCHAT_CONTAINER_PORT` | Webchat port |
| `NANOBOT_ACCESS_KEY` | Access key for web client authentication |
| `HOST_UID` / `HOST_GID` | Host user IDs for volume mount permissions |

### MCP Servers

Two MCP servers are configured:

1. **`lms`** — Exposes LMS backend API as tools:
   - `lms_health` — Check backend health
   - `lms_labs` — List available labs
   - `lms_pass_rates` — Get lab pass rates
   - `lms_scores` — Get lab scores
   - `lms_completion` — Get completion stats
   - `lms_groups` — Get student groups
   - `lms_timeline` — Get timeline data
   - `lms_top_learners` — Get top learners

2. **`webchat`** — Sends structured UI messages to the active chat:
   - `mcp_webchat_ui_message` — Deliver choice/confirm/composite payloads

### Channels

- **`webchat`** — WebSocket channel at `/ws/chat` (accessible via Caddy proxy)

## Dependencies

- **nanobot** — Agent framework (pinned commit from GitHub)
- **mcp-lms** — LMS MCP server (local, from `../mcp/mcp-lms`)
- **nanobot-webchat** — WebSocket channel plugin (from submodule)
- **mcp-webchat** — UI message MCP server (from submodule)

## Running Locally (Development)

### Prerequisites

1. Backend running at `http://localhost:42002`
2. Qwen Code API running at `http://localhost:42005`
3. `.env.docker.secret` populated with required keys

### Start the Agent

```bash
cd nanobot
uv sync
uv run nanobot agent --logs --session cli:dev -c ./config.json
```

### Test with MCP Tools

```bash
cd nanobot
NANOBOT_LMS_BACKEND_URL=http://localhost:42002 \
NANOBOT_LMS_API_KEY=YOUR_LMS_API_KEY \
uv run nanobot agent --logs --session cli:test -c ./config.json \
  -m "What labs are available?"
```

## Docker Deployment

### Build and Deploy

```bash
# Build the nanobot service
docker compose --env-file .env.docker.secret build nanobot

# Start all services
docker compose --env-file .env.docker.secret up -d
```

### Verify Deployment

```bash
# Check service status
docker compose --env-file .env.docker.secret ps

# View logs
docker compose --env-file .env.docker.secret logs nanobot --tail 50
```

### Test WebSocket Endpoint

```bash
# Using websocat
echo '{"content":"What labs are available?"}' | \
  websocat "ws://localhost:42002/ws/chat?access_key=YOUR_NANOBOT_ACCESS_KEY"

# Using Python (if websocat unavailable)
uv run python - <<'PY'
import asyncio
import json
import websockets

async def main():
    uri = "ws://localhost:42002/ws/chat?access_key=YOUR_NANOBOT_ACCESS_KEY"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"content": "What labs are available?"}))
        print(await ws.recv())

asyncio.run(main())
PY
```

### Access Web Client

Open `http://<your-vm-ip>:42002/flutter` in a browser and log in with `NANOBOT_ACCESS_KEY`.

## Skills

### LMS Skill (`workspace/skills/lms/SKILL.md`)

Teaches the agent:

- Which `lms_*` tools are available and when to use each
- To call `lms_labs` first when a lab parameter is missing
- To provide user-friendly lab labels for structured UI choices
- To format numeric results (percentages, counts)
- To keep responses concise

### Structured UI Skill (`workspace/skills/structured-ui/SKILL.md`)

Handles generic UI patterns:

- `choice` — Present multiple options to the user
- `confirm` — Ask for confirmation
- `composite` — Complex multi-part interactions

The LMS skill cooperates with this by providing good labels and values for the UI layer.

## Troubleshooting

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Login works, then chat disconnects | Stale browser state | Clear site data, log in again |
| Replies take a long time | Model/API latency | Check `qwen-code-api` and `nanobot` logs |
| `/flutter` loads old behavior | Stale frontend assets | Hard refresh the browser |
| Login works but no reply | Broken `/ws/chat` proxy | Check Caddy config, nanobot logs |
| Raw JSON in chat | `mcp-webchat` not wired | Verify MCP server is installed and configured |

### Debug Commands

```bash
# Check resolved config inside container
docker exec <nanobot-container> cat /app/nanobot/config.resolved.json

# Check MCP server connection
docker compose --env-file .env.docker.secret logs nanobot | grep "MCP server"

# Test direct WebSocket connection
docker compose --env-file .env.docker.secret exec nanobot \
  python -c "import websockets; print('OK')"
```

## Security Notes

- **Never commit secrets** — `.env.docker.secret` and `config.resolved.json` are gitignored
- **Access key protection** — The web client requires `NANOBOT_ACCESS_KEY` to connect
- **Backend API key isolation** — `NANOBOT_LMS_API_KEY` stays server-side; web clients use a separate access key

## Report

See `REPORT.md` for:

- Task 1A: Bare agent responses
- Task 1B: Agent with LMS tools
- Task 1C: Skill prompt effects
- Task 2A: Deployment logs
- Task 2B: Web client screenshots

## References

- [Nanobot Documentation](https://github.com/HKUDS/nanobot)
- [MCP Specification](https://modelcontextprotocol.io/)
- Task descriptions: `../lab/tasks/required/task-1.md`, `../lab/tasks/required/task-2.md`
