import json
import subprocess

from swe_ci.config import CONFIG


HOME_DIR = "/opt/agent/home"

def setup_opencode(
        container_name: str,
        ) -> None:

    AUTH_DIR = f"{HOME_DIR}/.local/share/opencode"
    CFG_DIR = f"{HOME_DIR}/.config/opencode"
    AUTH_FILE = "auth.json"
    CFG_FILE = "opencode.json"

    auth = {
        "custom": {
            "type": "api", 
            "key": CONFIG.api_key
        }
    }

    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "permission": "allow",
        "provider": {
            "custom": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "自定义",
                "options": {
                    "baseURL": CONFIG.base_url,
                },
                "models": {
                    CONFIG.model_name: {
                        "name": CONFIG.model_name,
                    }
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



def valid_and_parse(result: subprocess.CompletedProcess) -> dict:

    if result.returncode != 0:
        raise RuntimeError(
            f"Calling opencode failed. {result.returncode=}"
            f"stderr: {result.stderr}"    
        )

    # OpenCode 的输出是纯文本，不支持解析用量信息。
    return {
        "execution_time": 0,
        "input_tokens": 0,
        "output_tokens": 0
    }



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
    print(result, flush=True)
    return valid_and_parse(result)
