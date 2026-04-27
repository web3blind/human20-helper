from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import entrypoint  # type: ignore  # noqa: E402
import human20_mcp_client  # type: ignore  # noqa: E402


class StubClient:
    def list_tools(self):
        return {
            "result": {
                "tools": [
                    {"name": "get_progress"},
                    {"name": "get_onboarding"},
                    {"name": "get_pulse"},
                    {"name": "get_workshop_chat_json"},
                    {"name": "preview_user_message"},
                    {"name": "send_user_message"},
                ]
            }
        }

    def structured_tool(self, name, arguments=None):
        if name == "get_progress":
            return {"activeItem": "lesson-1", "completedItems": ["lesson-onboarding"]}
        if name == "get_onboarding":
            return {"summary": "start", "status": "resume", "nextMove": "continue"}
        if name == "get_pulse":
            return {
                "title": "Пульс",
                "updatedAt": "2026-04-24",
                "threads": [{"title": "A", "summary": "B"}],
            }
        if name == "get_whats_new":
            return {"summary": "new"}
        if name == "get_workshop_chat_json":
            return {
                "messageCount": 1,
                "messages": [{"message_id": 1, "text": "OpenClaw works", "from": "Chip"}],
            }
        if name == "get_content_detail":
            return {"item": {"title": "Lesson", "href": "/content/lesson-1"}, "attachments": []}
        if name == "get_transcript":
            return [{"text": "hello"}]
        if name == "get_homework_progress":
            return {"progress": {}}
        raise AssertionError(name)


class Human20HelperEntrypointTest(unittest.TestCase):
    def test_status_reports_missing_expected_tools(self) -> None:
        result = entrypoint.status(StubClient())
        self.assertTrue(result["ok"])
        self.assertIn("get_progress", result["has"])
        self.assertIn("get_content_detail", result["missing"])

    def test_chat_search_returns_matches(self) -> None:
        result = entrypoint.chat_search(StubClient(), "openclaw")
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["from"], "Chip")

    def test_lesson_context_uses_detail_transcript_and_homework(self) -> None:
        result = entrypoint.lesson_context(StubClient(), "lesson-1", None)
        self.assertEqual(result["title"], "Lesson")
        self.assertEqual(result["transcriptChunks"], 1)
        self.assertIn("get_homework_progress", result["sources"])

    def test_client_accepts_token_with_bearer_prefix(self) -> None:
        client = human20_mcp_client.Human20McpClient(
            base_url="https://human20.app/mcp",
            bearer_token="Bearer actual-token",
        )

        self.assertEqual(client.bearer_token, "actual-token")
        self.assertEqual(client._headers(include_session=False)["Authorization"], "Bearer actual-token")


if __name__ == "__main__":
    unittest.main()
