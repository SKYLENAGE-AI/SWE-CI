import json
import sqlite3
import tempfile
import subprocess
from pathlib import Path

from swe_ci.config import CONFIG


HOME_DIR = "/opt/agent/home"
AUTH_DIR = f"{HOME_DIR}/.local/share/opencode"
CFG_DIR = f"{HOME_DIR}/.config/opencode"
AUTH_FILE = "auth.json"
CFG_FILE = "opencode.json"

def setup_opencode(
        container_name: str,
        ) -> None:

    auth = {
        "custom": {
            "type": "api", 
            "key": CONFIG.api_key
        }
    }

    model_entry = {
        "name": CONFIG.model_name,
    }

    if hasattr(CONFIG, "llm_options") and CONFIG.llm_options:
        try:
            parsed_options = json.loads(CONFIG.llm_options)
        except json.JSONDecodeError as e:
            raise ValueError(f"CONFIG.llm_options is not a valid JSON format: {CONFIG.llm_options!r}") from e
        model_entry["options"] = parsed_options


    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "permission": "allow",
        "provider": {
            "custom": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "custom",
                "options": {
                    "baseURL": CONFIG.base_url,
                },
                "models": {
                    CONFIG.model_name: model_entry
                },
            }
        },
    }

    auth_payload = json.dumps(auth, indent=4, ensure_ascii=False) + "\n"
    cfg_payload = json.dumps(cfg, indent=4, ensure_ascii=False) + "\n"

    subprocess.run([
        "docker", "exec", "-i", "-u", "root", container_name, "sh", "-c", 
        f"mkdir -p {AUTH_DIR} && cat > {AUTH_DIR}/{AUTH_FILE}"
        ], input=auth_payload, text=True, check=True)

    subprocess.run([
        "docker", "exec", "-i", "-u", "root", container_name, "sh", "-c", 
        f"mkdir -p {CFG_DIR} && cat > {CFG_DIR}/{CFG_FILE}"
        ], input=cfg_payload, text=True, check=True)



def read_usage(db_path: str) -> dict:
    db = Path(db_path)
    if not db.exists():
        return {
            "input_tokens": None, 
            "output_tokens": None, 
            "execution_time": None,
            }

    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # Execution time from session table (millisecond timestamps)
    cursor.execute("SELECT time_created, time_updated FROM session LIMIT 1")
    row = cursor.fetchone()
    if row and row[0] and row[1]:
        execution_time = (row[1] - row[0]) / 1000.0
    else:
        execution_time = None

    # Token usage from message table
    cursor.execute("SELECT data FROM message")

    input_tokens = 0
    output_tokens = 0

    for (data_str,) in cursor.fetchall():
        data = json.loads(data_str)
        tokens = data.get("tokens")
        if not tokens:
            continue
        input_tokens += tokens.get("input", 0)
        output_tokens += tokens.get("output", 0)

    conn.close()
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "execution_time": execution_time}



def valid_and_parse(
        container_name: str,
        result: subprocess.CompletedProcess
        ) -> dict:

    if result.returncode != 0:
        raise RuntimeError(
            f"Calling opencode failed. {result.returncode=}"
            f"stderr: {result.stderr}"    
        )
    try:
        db_remote = f"{AUTH_DIR}/opencode.db"
        with tempfile.TemporaryDirectory() as tmpdir:
            local_db = Path(tmpdir) / "opencode.db"
            # Checkpoint WAL so all data is flushed into the main db file.
            subprocess.run(
                ["docker", "exec", container_name, "sqlite3", db_remote, "PRAGMA wal_checkpoint(TRUNCATE);"],
                capture_output=True, text=True,
            )
            subprocess.run(
                ["docker", "cp", f"{container_name}:{db_remote}", str(local_db)],
                capture_output=True, text=True, check=True
            )
            # WAL/SHM files are required — checkpoint may not work if sqlite3 is missing in the container
            for suffix in ["-wal", "-shm"]:
                subprocess.run(
                    ["docker", "cp", f"{container_name}:{db_remote}{suffix}", f"{local_db}{suffix}"],
                    capture_output=True, text=True,
                )
            usage = read_usage(str(local_db))
            return usage
    except Exception as e:
        raise RuntimeError(
            f"Failed to extract token usage from container {container_name}: {e}"
        ) from e



def call_opencode(
        container_name: str,
        prompt: str,
        *,
        work_dir: str = "/app",
        timeout: int,
        ) -> subprocess.CompletedProcess:
    
    setup_opencode(container_name)
    result = subprocess.run([
        "docker", "exec", "-w", work_dir,
        "-e", f"HOME={HOME_DIR}", "-e", "DISABLE_SEND_PV=1",
        container_name,
        "opencode", "run", "--model", f"custom/{CONFIG.model_name}", prompt,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return valid_and_parse(container_name, result)
