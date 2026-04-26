from __future__ import annotations

import argparse
import json
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


def main() -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
