import csv
import json
import shutil
import zipfile
import subprocess
from pathlib import Path


def read_csv(
    csv_path: str | Path,
) -> list[dict]:
    if not Path(csv_path).is_file():
        raise FileNotFoundError(f"File not found: {str(csv_path)}")
    data = []
    with open(str(csv_path), mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    return data


def unzip(
        zip_file: str | Path, 
        output_dir: str | Path,
        ) -> None:
    zip_file = Path(zip_file)
    if not zip_file.is_file():
        raise FileNotFoundError(f"File not found: {str(zip_file)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_file) as zf:
        zf.extractall(output_dir)


def copy_dir(
        src_dir: str | Path, 
        dst_dir: str | Path, 
        *,
        overwrite: bool = True
        ) -> None:
    src = Path(src_dir).resolve()
    dst = Path(dst_dir).resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"Directory not found: {str(src)}")
    if overwrite:
        shutil.rmtree(dst, ignore_errors=True)
    elif dst.is_dir():
        raise FileExistsError(f"Overwrite = False but {str(dst_dir)} exists.")
    shutil.copytree(src, dst)


def remove_pattern_files(
        target_dir: str | Path, 
        patterns: list[str], 
        *,
        recursive: bool = False
        ) -> None:
    target_dir = Path(target_dir).resolve()
    if not target_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {str(target_dir)}")
    for pattern in patterns:
        matches = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)
        for item in sorted(matches, key=lambda x: len(str(x)), reverse=True):
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def read_jsonl(file_path: str | Path) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open('r', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def save_completed_process(
        result: subprocess.CompletedProcess, 
        json_path: str | Path
        ) -> None:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(vars(result), indent=4, ensure_ascii=False), 
        encoding='utf-8'
        )
