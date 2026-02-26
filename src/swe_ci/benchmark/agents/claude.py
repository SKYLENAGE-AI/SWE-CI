from swe_ci.config import CONFIG


def call_claude(
        container_name: str, 
        prompt: str, 
        *,
        work_dir: str = "/app",
        timeout:int
        ) -> dict:
    
    result = subprocess.run([
        "docker", "exec", "-w", work_dir,
        "-e", "IFLOW_ENV=eval", "-e", "DISABLE_SEND_PV=1",
        container_name,
        "iflow", "-y", "-p", prompt
        ], check=True, capture_output=True, text=True, timeout=timeout)
    return valid_and_parse(result)
