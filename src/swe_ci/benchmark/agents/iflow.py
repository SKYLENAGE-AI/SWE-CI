import re
import json
import subprocess

from swe_ci.config import CONFIG



def setup_iflow(
        container_name: str,
        ) -> None:

    cfg_dict = {
        "selectedAuthType": CONFIG.iflow.auth_type,
        "apiKey": CONFIG.api_key,
        "baseUrl": CONFIG.base_url,
        "modelName": CONFIG.model_name,
        "searchApiKey": "",
        "disableAutoUpdate": True,
        "telemetry": {
            "enabled": False,
            "target": "gcp",
            "logPrompts": True
        },
        "sandbox": False
    }
    payload = json.dumps(cfg_dict, indent=4, ensure_ascii=False) + "\n"
    subprocess.run([
        "docker", "exec", "-i", "-u", "root", container_name, "sh", "-c", 
        "mkdir -p /opt/agent/home/.iflow && cat > /opt/agent/home/.iflow/settings.json"
        ], input=payload, text=True, check=True)


def valid_and_parse(
        result: subprocess.CompletedProcess
        ) -> dict:
    if result.returncode != 0:
        raise RuntimeError(f"call iflow failed. {result.returncode=}")
    try:
        info_match = re.search(r'<Execution Info>\s*(.*?)\s*</Execution Info>', result.stderr, re.DOTALL)
        json_str = info_match.group(1)
        exec_data = json.loads(json_str)
        tag_start_index = info_match.start()
        prefix_content = result.stderr[:tag_start_index].rstrip()
        lines = [line.strip() for line in prefix_content.split('\n') if line.strip()]
        prev_non_empty_line = lines[-1] if lines else ""
        token_usage = exec_data.get("tokenUsage", {})
        input_tokens = token_usage.get("input", 0)
        output_tokens = token_usage.get("output", 0)
        execution_time = exec_data.get("executionTimeMs")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occured when parsing result. stderr: {result.stderr}. error info:{repr(e)}")
    if prev_non_empty_line.lower().startswith("error"):
        raise RuntimeError(prev_non_empty_line)
    if input_tokens == 0 or output_tokens == 0:
        raise RuntimeError(f"{input_tokens=}, {output_tokens=}")
    return {
        "execution_time": execution_time / 1000,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }

def call_iflow(
        container_name: str, 
        prompt: str, 
        *,
        work_dir: str = "/app",
        timeout:int
        ) -> dict:
    setup_iflow(container_name)
    result = subprocess.run([
        "docker", "exec", "-w", work_dir,
        "-e", "IFLOW_ENV=eval", "-e", "DISABLE_SEND_PV=1",
        container_name,
        "iflow", "-y", "-p", prompt
        ], check=True, capture_output=True, text=True, timeout=timeout)
    return valid_and_parse(result)
