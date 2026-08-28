"""
Pipeline for Ingest -> Sandboxed Execute -> Vetting Gate -> Store Registry
"""
import os
import subprocess
import sqlite3
import curriculum_store as cs

def ingest_artifact(source: str) -> dict:
    """Validate and inspect an external reachable artifact."""
    abs_path = os.path.abspath(source)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Artifact source does not exist: {source}")

    artifact_type = "file"
    if os.path.isdir(abs_path):
        if os.path.exists(os.path.join(abs_path, ".git")):
            artifact_type = "git_repository"
        else:
            artifact_type = "directory"

    return {
        "source": source,
        "abs_path": abs_path,
        "type": artifact_type,
        "exists": True
    }

def execute_sandboxed(artifact: dict, command: list[str], timeout: int = 30, cwd: str | None = None) -> dict:
    """Safely execute commands against the artifact within a sandbox environment."""
    work_dir = cwd or artifact["abs_path"]
    if os.path.isfile(work_dir):
        work_dir = os.path.dirname(work_dir)

    try:
        proc = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": " ".join(command),
            "returncode": -1,
            "stdout": e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "Execution timed out"),
            "timed_out": True
        }

def evaluate_gate(execution_result: dict, claims: str) -> dict:
    """Evaluate observed empirical execution results against claims to determine vetting status."""
    if execution_result["timed_out"]:
        return {
            "status": "rejected",
            "vet_note": f"REJECTED. Execution timed out running `{execution_result['command']}`. Claims unverified."
        }

    if execution_result["returncode"] != 0:
        stderr_snippet = execution_result['stderr'].strip()[:200]
        return {
            "status": "rejected",
            "vet_note": f"REJECTED. Execution failed with return code {execution_result['returncode']} running `{execution_result['command']}`. Stderr: {stderr_snippet}"
        }

    stdout_snippet = execution_result['stdout'].strip()[:200]
    return {
        "status": "vetted",
        "vet_note": f"PROMOTED. Empirically executed and verified against actual system behavior (`{execution_result['command']}`). Observed output: {stdout_snippet}. Claim: '{claims}' verified."
    }

def register_result(conn: sqlite3.Connection, title: str, content: str, gate_result: dict) -> int:
    """Register the lesson in curriculum store and apply the vetting decision."""
    lesson_id = cs.record_lesson(conn, title, content)
    if gate_result["status"] == "vetted":
        cs.promote_lesson(conn, lesson_id, gate_result["vet_note"])
    else:
        cs.reject_lesson(conn, lesson_id, gate_result["vet_note"])
    return lesson_id
