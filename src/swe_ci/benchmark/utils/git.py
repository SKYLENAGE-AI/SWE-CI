import subprocess
from pathlib import Path


def checkout(
        repo_dir: str | Path, 
        commit_sha: str,
        ) -> None:
    repo_dir = Path(repo_dir).resolve()
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {str(repo_dir)}")
    subprocess.run([
        "git", "-C", str(repo_dir), "checkout", "--force", "--detach", commit_sha
        ], check=True, capture_output=True, text=True)
