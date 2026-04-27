from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from human20_mcp_client import Human20McpClient


EXPECTED_TOOLS = {
    "get_progress",
    "get_onboarding",
    "get_whats_new",
    "get_pulse",
    "get_workshop_chat_json",
    "get_content_detail",
    "get_transcript",
    "get_homework_progress",
    "preview_user_message",
    "send_user_message",
}

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "helper_flow.py"
PYTHON = "python3"


def _tool_names(payload: dict[str, Any]) -> set[str]:
    return {
        tool.get("name", "")
        for tool in payload.get("result", {}).get("tools", [])
        if isinstance(tool, dict)
    }


def status(client: Human20McpClient) -> dict[str, Any]:
    tools = _tool_names(client.list_tools())
    return {
        "ok": True,
        "has": sorted(tools & EXPECTED_TOOLS),
        "missing": sorted(EXPECTED_TOOLS - tools),
        "extra": sorted(tools - EXPECTED_TOOLS),
    }


def where_am_i(client: Human20McpClient, user_id: str | None) -> dict[str, Any]:
    args = {"userId": user_id} if user_id else {}
    progress = client.structured_tool("get_progress", args)
    onboarding = client.structured_tool("get_onboarding", args)
    return {
        "progress": progress,
        "onboarding": onboarding,
        "nextMove": onboarding.get("nextMove") if isinstance(onboarding, dict) else None,
    }


def what_new(client: Human20McpClient) -> dict[str, Any]:
    pulse = client.structured_tool("get_pulse", {})
    whats_new = client.structured_tool("get_whats_new", {})
    return {"pulse": pulse, "whatsNew": whats_new}


def chat_search(client: Human20McpClient, query: str) -> dict[str, Any]:
    chat = client.structured_tool("get_workshop_chat_json", {})
    messages = chat.get("messages", []) if isinstance(chat, dict) else []
    query_lower = query.lower()
    matches = [
        message
        for message in messages
        if query_lower in json.dumps(message, ensure_ascii=False).lower()
    ]
    return {
        "query": query,
        "count": len(matches),
        "matches": matches[:20],
        "truncated": len(matches) > 20,
    }


def lesson_context(client: Human20McpClient, item_id: str, user_id: str | None) -> dict[str, Any]:
    detail = client.structured_tool("get_content_detail", {"item_id": item_id})
    transcript = client.structured_tool("get_transcript", {"item_id": item_id})
    homework = client.structured_tool("get_homework_progress", {})

    item = detail.get("item", {}) if isinstance(detail, dict) else {}
    attachments = detail.get("attachments", []) if isinstance(detail, dict) else []
    transcript_items = transcript.get("result") if isinstance(transcript, dict) else transcript
    return {
        "id": item_id,
        "title": item.get("title"),
        "href": item.get("href"),
        "attachments": attachments,
        "transcriptChunks": len(transcript_items) if isinstance(transcript_items, list) else None,
        "transcript": transcript_items,
        "homework": homework,
        "sources": ["get_content_detail", "get_transcript", "get_homework_progress"],
    }


def run_helper(args: list[str]) -> int:
    cmd = [PYTHON, str(HELPER), *args]
    completed = subprocess.run(cmd, cwd=str(ROOT), text=True)
    return completed.returncode


def infer_mode(query: str):
    q = query.lower().strip()
    verify_intent = any(x in q for x in ["проверь, что я сделал", "проверь что я сделал", "что не хватает", "чего не хватает", "проверь", "провер"])
    if verify_intent:
        lesson_match = re.search(r"lesson-(\d+)|урок\w*\s*(\d+)", q)
        if lesson_match:
            lesson_num = lesson_match.group(1) or lesson_match.group(2)
            return ("verify", f"lesson-{lesson_num}", None)
        return ("verify", None, None)

    if any(x in q for x in ["веди дальше", "что делать дальше", "что делать сейчас", "next action"]):
        return ("next-action", None, None)

    lesson_match = re.search(r"(lesson-\d+|урок\w*\s*(\d+))", q)
    if lesson_match:
        lesson_id = lesson_match.group(1)
        if lesson_id.startswith("урок"):
            lesson_id = f"lesson-{lesson_match.group(2)}"
        return ("continue", lesson_id, None)

    date_match = re.search(r"(20\d\d-\d\d-\d\d)", q)
    if any(x in q for x in ["с ", "since", "пропустил", "изменилось с", "changed since"]) and date_match:
        return ("changed-since", None, f"{date_match.group(1)}T00:00:00Z")

    if any(x in q for x in ["что нового", "whats new", "what's new", "нового"]):
        return ("whats-new", None, None)

    if any(x in q for x in ["test trainer", "test-trainer", "тест тренер", "тестовый тренер", "test mode", "тестовый режим"]):
        return ("test-trainer", None, None)

    if any(x in q for x in ["дальше", "следующий шаг", "где я", "прогресс", "summary", "состояние"]):
        return ("human", None, None)

    return ("human", None, None)


def main() -> int:
    commands = {"status", "where-am-i", "what-new", "chat-search", "lesson-context"}
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        parser = argparse.ArgumentParser(description="Human20 helper skill entrypoint")
        subparsers = parser.add_subparsers(dest="command", required=True)

        subparsers.add_parser("status")

        where = subparsers.add_parser("where-am-i")
        where.add_argument("--user-id")

        subparsers.add_parser("what-new")

        search = subparsers.add_parser("chat-search")
        search.add_argument("query")

        lesson = subparsers.add_parser("lesson-context")
        lesson.add_argument("item_id")
        lesson.add_argument("--user-id")

        args = parser.parse_args()
        client = Human20McpClient()

        if args.command == "status":
            result = status(client)
        elif args.command == "where-am-i":
            result = where_am_i(client, args.user_id)
        elif args.command == "what-new":
            result = what_new(client)
        elif args.command == "chat-search":
            result = chat_search(client, args.query)
        elif args.command == "lesson-context":
            result = lesson_context(client, args.item_id, args.user_id)
        else:
            parser.error(f"unknown command: {args.command}")

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    parser = argparse.ArgumentParser(description="human20-helper smart entrypoint")
    parser.add_argument("query", nargs="*", help="Natural language intent")
    parser.add_argument("--mode", choices=["human", "continue", "verify", "next-action", "changed-since", "whats-new", "test-trainer", "autopass-experiment"])
    parser.add_argument("--lesson")
    parser.add_argument("--since")
    args = parser.parse_args()

    if args.mode:
        if args.mode == "continue":
            if not args.lesson:
                raise SystemExit("--lesson is required with --mode continue")
            return run_helper(["--mode", "continue", "--lesson", args.lesson])
        if args.mode == "changed-since":
            if not args.since:
                raise SystemExit("--since is required with --mode changed-since")
            return run_helper(["--mode", "changed-since", "--since", args.since])
        if args.mode == "verify":
            helper_args = ["--mode", "verify"]
            if args.lesson:
                helper_args.extend(["--lesson", args.lesson])
            return run_helper(helper_args)
        if args.mode == "next-action":
            return run_helper(["--mode", "next-action"])
        return run_helper(["--mode", args.mode])

    query = " ".join(args.query).strip()
    mode, lesson, since = infer_mode(query)
    if mode == "continue":
        return run_helper(["--mode", "continue", "--lesson", lesson])
    if mode == "verify":
        helper_args = ["--mode", "verify"]
        if lesson:
            helper_args.extend(["--lesson", lesson])
        return run_helper(helper_args)
    if mode == "next-action":
        return run_helper(["--mode", "next-action"])
    if mode == "changed-since":
        return run_helper(["--mode", "changed-since", "--since", since])
    if mode == "whats-new":
        return run_helper(["--mode", "whats-new"])
    if mode == "test-trainer":
        return run_helper(["--mode", "test-trainer"])
    return run_helper(["--mode", "human"])


if __name__ == "__main__":
    raise SystemExit(main())
