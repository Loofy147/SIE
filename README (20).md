# SIE Curriculum System

Answers the question that started this: yes, "This" (the SIE mentorship notebook)
can be a full system — and it needed to be, because the ad-hoc version already lost
data mid-conversation before this fix existed.

## Execution Pipeline & Vetting Gate
The system implements a four-stage pipeline (`pipeline.py`) that handles external reachable artifacts end-to-end:
1. **Ingest (`ingest_artifact`)**: Validates and inspects external artifacts (git repos, files, directories).
2. **Execute (`execute_sandboxed`)**: Safely executes commands within isolation boundaries (subprocess, cwd trapping, output capturing, timeout).
3. **Vetting Gate (`evaluate_gate`)**: Compares observed stdout/stderr/exit codes against stated claims to determine promotion (`vetted`) or failure (`rejected`).
4. **Registry (`register_result`)**: Records the resulting lesson in `curriculum.db` via `curriculum_store.py` with timestamped vetting notes.

## Lessons Status
- **Lesson 1** (`vetted`): Git object model — tested against real git execution & hash reuse.
- **Lesson 2** (`vetted`): Design before implementation — six-step forcing function.
- **Lesson 3** (`vetted`): Wrong-first break-tested & corrected — auth/session system & mutable state rule.
- **Lesson 4** (`vetted`): Automated Artifact Ingestion & Sandboxed Gate Pipeline — empirically executed against repository artifact (`.`) via `git rev-parse HEAD`.

## Files
- `curriculum_store.py` — authoritative owner of the lesson log and standing gap (SQLite).
- `pipeline.py` — ingest -> execute -> gate -> registry pipeline runner.
- `test_pipeline.py` — unit tests for the artifact pipeline.
- `curriculum.db` — SQLite database with lessons 1–4 and updated standing gap.
- `mcp_server.py` — thin FastMCP adapter.
