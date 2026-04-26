# Human20 helper: investigation of 401 on content detail/transcript

## Summary

The new upstream `human20-helper` initially failed because it did not implement MCP session lifecycle. That part was fixed locally.

After fixing session handling, `get_content_detail` and `get_transcript` still fail with `401 Unauthorized` for the current Human20 bearer token, while several other read-only tools work with the same token and same MCP session.

## What was fixed locally

- Added proper MCP session lifecycle to the local `scripts/human20_mcp_client.py`:
  - `initialize`
  - capture `MCP-Session-Id`
  - `notifications/initialized`
  - session reuse
  - retry on `Session not found`
- Fixed `lesson-context` argument names to match real tool schemas (`item_id` instead of `id`).

This rules out the previous client-side/session-lifecycle issue for the failing calls below.

## Reproduction

Working calls with the same token and same MCP session:
- `tools/list`
- `get_progress`
- `get_onboarding`
- `get_whats_new`
- `get_pulse`
- `get_workshop_chat_json`
- `get_workshop`
- `get_digest`
- `get_changed_since`
- `search`
- `get_homework_progress`

Failing calls with the same token and same MCP session:
- `get_content_detail {"item_id":"lesson-1"}`
- `get_transcript {"item_id":"lesson-1"}`
- `get_content_detail {"item_id":"extra-openclaw-business"}`
- `get_transcript {"item_id":"extra-openclaw-business"}`

Observed errors:
- `GET /v1/content/lesson-1/detail failed with 401 ... Unauthorized`
- `GET /v1/content/lesson-1/transcript failed with 401 ... Unauthorized`
- `GET /v1/content/extra-openclaw-business/detail failed with 401 ... Unauthorized`
- `GET /v1/content/extra-openclaw-business/transcript failed with 401 ... Unauthorized`

## Important evidence

1. The MCP session itself is valid.
   - Before fixing session lifecycle, calls failed with `Missing session ID` / `Session not found`.
   - After fixing lifecycle, many MCP tools work correctly.

2. The bearer token is not globally invalid/expired.
   - If the token were simply dead, the working tools above would also fail.
   - Instead, only a subset of backend routes fails.

3. Argument shape is not the cause.
   - Tool schemas were inspected from `tools/list`.
   - `get_content_detail` and `get_transcript` both require `item_id`.
   - Calls were repeated with correct argument names.
   - The backend then reached the route and returned `401`, not a validation error.

4. The failure is route-specific.
   - Same token/session can read workshop/progress/digest/chat/homework/search.
   - Same token/session cannot read `/v1/content/:item_id/detail` or `/v1/content/:item_id/transcript`.

## Likely cause

This looks like a Human20 backend authorization/scope mismatch for content-detail/transcript routes, not a local client bug.

Most likely explanations:
- the current bearer token lacks permission for `content detail` / `transcript` routes while still being allowed to access progress/workshop/chat/digest routes;
- or the MCP server exposes these tools in `tools/list`, but the underlying backend routes are misconfigured for this token/account;
- or there is a regression in Human20 route-level auth for `/v1/content/*/detail` and `/v1/content/*/transcript`.

## What to tell the Human20 testing chat

- The upstream public helper also had a broken MCP client for session-based servers; that part was fixed locally.
- After session handling was fixed, `get_content_detail` and `get_transcript` still reproducibly return `401 Unauthorized`.
- This happens with correct `item_id`, valid MCP session, and the same bearer token that successfully works for multiple other read-only tools.
- Therefore the remaining blocker appears to be server-side auth/scope/routing for content detail/transcript endpoints, not the client implementation.

## Recommended next checks on Human20 side

1. Verify whether the current bearer token is expected to have access to:
   - `GET /v1/content/:item_id/detail`
   - `GET /v1/content/:item_id/transcript`
2. Compare route auth middleware for these endpoints against the routes used by:
   - `get_workshop`
   - `get_progress`
   - `get_digest`
   - `get_workshop_chat_json`
3. Check whether MCP advertises tools that the current token/account is not actually allowed to use.
4. If token refresh is supposed to fix it, confirm that explicitly; current evidence suggests the token is not globally expired, because many other tools work.
