# SIE Curriculum system

Answers the question that started this: yes, "This" (the SIE mentorship notebook)
can be a full system — and it needed to be, because the ad-hoc version already lost
data mid-conversation before this fix existed (lessons 1 and 2 vanished from disk
between tool calls in the same chat; recovered from conversation context, not from
files, into `curriculum.db`).

## What's tested vs. what isn't, and why
- `curriculum_store.py` — pure stdlib (sqlite3), zero external deps. Fully executed
  and verified in the build sandbox: all 3 lessons seeded, round-trip checked byte
  for byte, gap read back correctly.
- `mcp_server.py` — written to the documented FastMCP shape, but **not executed**
  in the build sandbox. That sandbox's egress proxy rejects pypi.org
  (`x-deny-reason: host_not_allowed`) even though pypi.org is nominally on its
  allowed-domains list — confirmed against an uncached package, not just `mcp`.
  This is a constraint of the build environment, not of your machine.

## Setup (on your machine, where pypi access is normal)
```
pip install "mcp[cli]"
cd sie/system
python3 mcp_server.py          # should start and idle, no errors
mcp dev mcp_server.py          # opens MCP Inspector — call list_lessons, get_gap, etc.
mcp install mcp_server.py      # registers it directly with Claude Desktop
```

## Why only MCP, no REST API
Applying the same justification test as the lessons: a REST API is only warranted
once a second, non-agent consumer exists (a browser dashboard, some other tool).
Right now the only real consumer is Claude sessions wanting continuity — that's
exactly MCP's job. Adding REST later costs little: it would be a second thin
adapter over the same `curriculum_store.py`, not a second store.

## Files
- `curriculum_store.py` — the Curriculum Store. Single authoritative owner of the
  lesson log (append-only) and the standing gap (singleton, mutable).
- `curriculum.db` — seeded with lessons 1–3, recovered and verified.
- `mcp_server.py` — thin MCP adapter. Owns no state.

## The vetting gate
`status` defaults to `unvetted` on insert. Nothing is treated as reusable until
`promote_lesson(id, note)` is called explicitly, with a real reason on record —
proven three times over already: our own lessons 1–3 sat unvetted until this was
added, and lesson 1 (empirically tested against real git behavior) got promoted
on stronger evidence than lessons 2–3 (reasoned examples, never executed as code) —
the note field carries that distinction instead of hiding it behind one boolean.

What this does NOT yet do: there is no execution sandbox, and nothing here ingests
external material (a real repo, API, or paper) yet. The gate only governs content
someone explicitly wrote to the store — it has never been tested against something
untrusted. That's the honest next test, not a solved problem.
