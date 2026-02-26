from pathlib import Path
from huggingface_hub.utils import disable_progress_bars
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

from swe_ci.benchmark.utils import read_csv
from swe_ci.config import CONFIG


def all_splitting(
        repo_id: str
        ) -> list[str]:
    api = HfApi()
    files = api.list_repo_tree(
        repo_id = repo_id, 
        path_in_repo = "metadata", 
        repo_type = "dataset", 
        recursive = True,
        token = CONFIG.hf_token
    )
    return [
        Path(f.path).stem for f in files 
        if f.path.endswith('.csv')
    ]


def download_file(
        repo_id: str, 
        remote_file_path: str, 
        local_root_dir: str,
        hf_token: str | None = None
        ) -> str:
    return hf_hub_download(
        repo_id = repo_id,
        filename = remote_file_path,
        repo_type = "dataset",
        local_dir = local_root_dir,
        token = hf_token
    )


def download_hf_folder(
        repo_id: str, 
        remote_folder_path: str, 
        local_root_dir: str,
        hf_token: str | None = None
        ) -> str:
    return snapshot_download(
        repo_id = repo_id,
        repo_type = "dataset",
        allow_patterns = [f"{remote_folder_path}/**"],
        local_dir = local_root_dir,
        token = hf_token
    )
 

def download_dataset() -> None:
    disable_progress_bars()
    hf_token = None if CONFIG.hf_token == "none" else CONFIG.hf_token
    all_split = all_splitting(CONFIG.hf_repo_id)
    if CONFIG.splitting not in all_split:
        raise ValueError(f"Expected splitting in {all_split}, but got {CONFIG.splitting}")
    metadata_path = download_file(
        CONFIG.hf_repo_id, f"metadata/{CONFIG.splitting}.csv", CONFIG.save_root_dir, hf_token
        )
    metadata = read_csv(metadata_path)
    task_ids = [task['task_id'] for task in metadata]
    total = len(task_ids)
    for idx, task_id in enumerate(task_ids):
        print(f"({idx+1}/{total}) Preparing {task_id}...", end="    ", flush=True)
        download_hf_folder(CONFIG.hf_repo_id, f"data/{task_id}", CONFIG.save_root_dir, hf_token)
        print(f"Done.", flush=True)


if __name__ == "__main__":
    download_dataset()
