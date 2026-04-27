# human20-helper

MVP helper для Human20.

Source of truth теперь находится прямо в `skills/human20-helper/`.
Старый каталог `ai-projects/human20-helper/` не должен считаться runtime-источником для skill.

## Что делает текущая версия

- читает структуру и guidance из Human20 через direct MCP session flow;
- не зависит от проблемного OpenClaw MCP bridge;
- локально сверяет прохождение уроков по workspace/config/memory/project evidence;
- определяет следующий непройденный или не подтверждённый этап;
- возвращает ссылку на урок и practical next step;
- умеет делать continuation по конкретному уроку;
- умеет выбирать режим по простому текстовому запросу;
- умеет test-only trainer/orchestrator fallback для последовательного lesson flow.

## Конфиг

Поддерживаются 2 способа:

1. Через переменные окружения
2. Через локальный `.env` рядом со скриптами, то есть в корне skill-проекта `skills/human20-helper/.env`

Используются переменные:
- `HUMAN20_BEARER_TOKEN`
- `HUMAN20_MCP_URL` (optional, по умолчанию `https://human20.app/mcp`)

Важно:
- можно указывать как сам токен,
- так и строку вида `Bearer <token>`;
- helper нормализует это автоматически.

## Скрипты

### 1. Direct MCP client

```bash
python3 skills/human20-helper/scripts/human20_mcp_client.py tools/list
python3 skills/human20-helper/scripts/human20_mcp_client.py tools/call --tool get_workshop
python3 skills/human20-helper/scripts/human20_mcp_client.py tools/call --tool get_progress
```

### 2. Local evidence audit

```bash
python3 skills/human20-helper/scripts/local_evidence.py
```

### 3. Basic helper flow

Human-readable summary:
```bash
python3 skills/human20-helper/scripts/helper_flow.py --mode human
```

What changed since date:
```bash
python3 skills/human20-helper/scripts/helper_flow.py --mode changed-since --since 2026-04-01T00:00:00Z
```

Continuation for one lesson:
```bash
python3 skills/human20-helper/scripts/helper_flow.py --mode continue --lesson lesson-4
```

Test-only trainer/orchestrator mode:
```bash
python3 skills/human20-helper/scripts/helper_flow.py --mode test-trainer
```

### 4. Smart entrypoint

Summary / current state:
```bash
python3 skills/human20-helper/scripts/entrypoint.py "где я сейчас"
```

What's new:
```bash
python3 skills/human20-helper/scripts/entrypoint.py "что нового"
```

Continuation for one lesson:
```bash
python3 skills/human20-helper/scripts/entrypoint.py "урок 4"
```

Test-only trainer/orchestrator mode:
```bash
python3 skills/human20-helper/scripts/entrypoint.py "тестовый режим"
```

При этом старые технические команды тоже поддерживаются:

```bash
python3 skills/human20-helper/scripts/entrypoint.py status
python3 skills/human20-helper/scripts/entrypoint.py where-am-i --user-id tg:123
python3 skills/human20-helper/scripts/entrypoint.py chat-search "openclaw"
python3 skills/human20-helper/scripts/entrypoint.py lesson-context lesson-1 --user-id tg:123
```

## Ограничения текущей фазы

- guided progression уже поднят в runtime, но это ещё не полноценный beginner-first course companion;
- homework-aware write-back уже встроен в guided flow, но только при высокой уверенности и только через локальный mapping `lesson_rules.json`;
- test-only trainer mode не пишет в Human20 и нужен только как безопасная симуляция;
- evidence engine пока опирается на фиксированные локальные признаки и ещё требует дальнейшего усиления.

### Важный нюанс по homework sync

Сейчас helper умеет автоматически синхронизировать homework/progress только потому, что знает ожидаемые `task_id` из локального `lesson_rules.json`.

Что приходит live:
- `get_homework_progress` даёт уже отмеченные `task_id`;
- `get_content_detail` / `sections` / `promptCards` дают человеческий текст заданий.

Чего пока не хватает для полностью нативной системы:
- канонического API-поля или tool, который отдаёт для каждого урока полный каталог homework tasks:
  - `task_id`
  - `label`
  - `description`
  - `completed`

Пока такого каталога нет, helper использует semi-manual mapping и специально блокирует write-back, если live `task_id` начинают расходиться с локальным ожиданием.

## Safety

- Read-only by default for discovery commands.
- Push messages must go through backend-owned MCP tools: `preview_user_message` first, then `send_user_message`.
- Do not put bearer tokens, Telegram bot tokens, Supabase keys, or user exports into this repo.
