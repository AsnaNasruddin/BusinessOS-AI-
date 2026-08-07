"""Built-in tool registry (Phase 2). Tools are code, not org data — there's
no `tools` table; this static list is the source of truth an Agent's
`allowed_tools` field references by name. Actually calling out to send an
email, hit the KB, etc. is Phase 4+ work — for now this gives agents
something real to declare and the UI something real to list, matching
frontend/src/lib/seed-data.ts's mock set."""

from app.schemas.agent import ToolOut

BUILTIN_TOOLS: list[ToolOut] = [
    ToolOut(
        id="search_kb",
        name="search_kb",
        display_name="search_kb",
        description="Vector search over a knowledge base.",
        category="retrieval",
    ),
    ToolOut(
        id="send_email",
        name="send_email",
        display_name="send_email",
        description="Sends an approved reply. Stubbed in dev.",
        category="communication",
    ),
    ToolOut(
        id="log_activity",
        name="log_activity",
        display_name="log_activity",
        description="Writes an interaction record to the CRM.",
        category="data",
    ),
    ToolOut(
        id="http_request",
        name="http_request",
        display_name="http_request",
        description="Generic outbound HTTP call.",
        category="data",
    ),
]

TOOL_NAMES = {tool.name for tool in BUILTIN_TOOLS}


def list_tools() -> list[ToolOut]:
    return BUILTIN_TOOLS
