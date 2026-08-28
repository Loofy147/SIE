"""
SIE Curriculum MCP server — thin adapter, owns no state itself.
Exposes curriculum_store.py's operations as MCP tools so any Claude session
(this one's successors included) can read/write curriculum state directly,
instead of re-deriving lost context from scratch each time.

NOT executed inside the build sandbox — that sandbox's egress proxy blocks
pypi.org (confirmed: `pip install mcp` fails there with host_not_allowed even
though pypi.org is nominally allowlisted). Written to the documented FastMCP
API shape (mcp.server.fastmcp.FastMCP, @mcp.tool() decorators, mcp.run()).
Verify on your own machine, where pypi access is normal:

    pip install "mcp[cli]"
    python3 mcp_server.py                 # sanity check it starts
    mcp dev mcp_server.py                 # interactive test via MCP Inspector
    mcp install mcp_server.py             # registers it with Claude Desktop directly
"""
import os
from mcp.server.fastmcp import FastMCP
import curriculum_store as cs

DB_PATH = os.path.join(os.path.dirname(__file__), "curriculum.db")
_conn = cs.init_db(DB_PATH)

mcp = FastMCP("sie-curriculum")


@mcp.tool()
def record_lesson(title: str, content: str) -> int:
    """Record a completed SIE lesson (dissection or design derivation) durably.
    Returns the new lesson id."""
    return cs.record_lesson(_conn, title, content)


@mcp.tool()
def list_lessons(status: str | None = None) -> list[dict]:
    """List recorded lessons: id, title, created_at, status. Pass status='vetted' to see
    only material that's actually cleared the gate, not everything ever recorded."""
    return cs.list_lessons(_conn, status)


@mcp.tool()
def get_lesson(lesson_id: int) -> dict | None:
    """Retrieve one lesson's full content plus status/vetted_at/vet_note."""
    return cs.get_lesson(_conn, lesson_id)


@mcp.tool()
def promote_lesson(lesson_id: int, note: str) -> None:
    """The gate. Mark a lesson as vetted — requires an explicit, on-record reason.
    Never call this just because something ran without erroring; say what evidence
    actually supports reuse."""
    cs.promote_lesson(_conn, lesson_id, note)


@mcp.tool()
def reject_lesson(lesson_id: int, note: str) -> None:
    """Mark a lesson as rejected, with the reason on record."""
    cs.reject_lesson(_conn, lesson_id, note)


@mcp.tool()
def get_gap() -> str | None:
    """Get the current standing gap: what hasn't been independently produced yet.
    Read this at the start of a new session instead of re-deriving curriculum state."""
    return cs.get_gap(_conn)


@mcp.tool()
def set_gap(text: str) -> None:
    """Update the standing gap after an exercise is completed or reassessed."""
    cs.set_gap(_conn, text)


if __name__ == "__main__":
    mcp.run()
