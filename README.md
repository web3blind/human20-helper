# Human2 Helper Skill

Public Codex/OpenClaw-compatible skill for working with the Human20 API/MCP surface.

This repository contains no secrets. Provide your own `HUMAN20_BEARER_TOKEN` locally through `.env` or environment variables.

## Setup

```powershell
git clone https://github.com/evgyur/human2-helper.git
cd human2-helper
Copy-Item .env.example .env
```

Fill `.env`:

```env
HUMAN20_BEARER_TOKEN=your-token
HUMAN20_MCP_URL=https://human20.app/mcp
```

## Commands

```powershell
python scripts/entrypoint.py status
python scripts/entrypoint.py where-am-i --user-id tg:123
python scripts/entrypoint.py what-new
python scripts/entrypoint.py chat-search "openclaw"
python scripts/entrypoint.py lesson-context lesson-1 --user-id tg:123
```

## Safety

- Read-only by default for discovery commands.
- Push messages must go through backend-owned MCP tools: `preview_user_message` first, then `send_user_message`.
- Do not put bearer tokens, Telegram bot tokens, Supabase keys, or user exports into this repo.
