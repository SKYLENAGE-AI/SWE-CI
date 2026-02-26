import os
import json
import tarfile
import subprocess
from typing import Sequence
from subprocess import CompletedProcess
from pathlib import Path, PurePosixPath

# --- Check status ---

def has_image(image_tag: str) -> bool:
    result = subprocess.run([
        "docker", "image", "inspect", image_tag
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def has_container(container_name: str) -> bool:
    result = subprocess.run([
        "docker", "container", "inspect", container_name
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

# --- Clear resouce ---

def remove_image(image_tag: str) -> None:
    subprocess.run([
        "docker", "rmi", "-f", image_tag
        ], check=True, capture_output=True, text=True)


def remove_container(container_name: str) -> None:
    subprocess.run([
        "docker", "rm", "-f", container_name
        ], check=True, capture_output=True, text=True)
 

def remove_item_from_container(
        container_name: str, 
        target_path: str | Path
        ) -> CompletedProcess:
    target_path = PurePosixPath(target_path)
    return subprocess.run([
        "docker", "exec", container_name, "rm", "-rf", str(target_path)
        ], check=True, capture_output=True, text=True)

# --- Image operations ---

def build_image_from_dockerfile(
        image_tag: str, 
        dockerfile_path: str | Path, 
        *,
        context_dir: str | Path | None = None, 
        extra_args: Sequence[str] | None = None,
        overwrite: bool = True
        ) -> None:
    context_dir = "." if context_dir is None else context_dir
    if has_image(image_tag):
        if not overwrite:
            raise FileExistsError(f"Image tag {image_tag} already exists. Set overwrite=True to rebuild.")
        remove_image(image_tag) 
    
    subprocess.run([
        "docker", "build", "-t", image_tag, "-f", str(dockerfile_path),
        *(extra_args or []), str(context_dir)
    ], check=True, capture_output=True, text=True)


def save_image_to_tar(image_tag: str, output_path: str | Path) -> None:
    output_path = str(output_path)
    temp_path = f"{output_path}.tmp"
    cmd = f"docker save {image_tag} | gzip > {temp_path}"
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        os.replace(temp_path, output_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def read_image_tag_from_tar(tar_path: str | Path) -> str:
    tar_path = Path(tar_path)
    with tarfile.open(tar_path, "r:gz") as tar:
        manifest_file = tar.extractfile("manifest.json")
        if not manifest_file:
            raise FileNotFoundError(f"manifest.json not found in {tar_path}")
        tag = json.load(manifest_file)[0]["RepoTags"][0]
    return tag


def load_image_from_tar(tar_path: str | Path, *, exist_ok: bool) -> str:
    image_tag = read_image_tag_from_tar(tar_path)
    if has_image(image_tag):
        if exist_ok:
            return image_tag
        else:
            raise FileExistsError(f"Image tag {image_tag} already exists.")
    subprocess.run([
        "docker", "load", "-i", str(tar_path)
        ], check=True, capture_output=True, text=True)
    return image_tag

# --- Container operations ---

def run_container(
        image_tag: str, 
        container_name: str, 
        *, 
        extra_args: Sequence[str] | None = None,
        overwrite: bool = False) -> None:
    if has_container(container_name):
        if overwrite:
            remove_container(container_name)
        else:
            raise FileExistsError(f"Container {container_name} already exists.")
            
    subprocess.run([
        "docker", "run", "-d", "--init", "--name", container_name,
        "--rm", *(extra_args or []), image_tag, "tail", "-f", "/dev/null"
    ], check=True, capture_output=True, text=True)


def make_container_dir(container_name: str, dir_path: str | Path) -> None:
    dir_path = PurePosixPath(dir_path)
    subprocess.run([
        "docker", "exec", container_name, "mkdir", "-p", str(dir_path)
    ], check=True, capture_output=True, text=True)


def has_container_dir(container_name: str, dir_path: str | Path) -> bool:
    dir_path = PurePosixPath(dir_path)
    result = subprocess.run([
        "docker", "exec", container_name, "test", "-d", str(dir_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def has_container_file(container_name: str, file_path: str | Path) -> bool:
    file_path = PurePosixPath(file_path)
    result = subprocess.run([
        "docker", "exec", container_name, "test", "-f", str(file_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def is_container_dir_empty(container_name: str, dir_path: str | Path) -> bool:
    dir_path = PurePosixPath(dir_path)
    result = subprocess.run([
        "docker", "exec", container_name, "sh", "-c", f'[ -z "$(ls -A {str(dir_path)})" ]'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def copy_file_to_container(
        container_name: str, 
        src_file: str | Path, 
        dst_dir: str | Path,
        *,
        rename: str | None = None,
        mkdir: bool = False,
        overwrite: bool = False
        ) -> None:
    src_file = Path(src_file)
    dst_dir = PurePosixPath(dst_dir)
    if not src_file.is_file():
        raise FileNotFoundError(f"File not found: {str(src_file)}")
    if not has_container(container_name):
        raise FileNotFoundError(f"Container not found: {container_name}")
    if not has_container_dir(container_name, dst_dir):
        if not mkdir:
            raise FileNotFoundError(f"Directory not found: {str(dst_dir)}")
        else:
            make_container_dir(container_name, dst_dir)
    target_path = dst_dir / (rename or src_file.name)
    if has_container_file(container_name, target_path) and not overwrite:
        raise FileExistsError(f"File already exist: {str(target_path)}")
    subprocess.run([
        "docker", "cp", str(src_file), f"{container_name}:{str(target_path)}"
        ], check=True, capture_output=True, text=True)


def copy_dir_to_container(
        container_name: str, 
        src_dir: str | Path, 
        dst_dir: str | Path, 
        *,
        contents_only: bool = False
        ) -> None:
    src_dir = Path(src_dir)
    dst_dir = PurePosixPath(dst_dir)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"File not found: {src_dir}")
    dst_dir_s = str(dst_dir).rstrip("/")
    if not has_container_dir(container_name, dst_dir_s):
        make_container_dir(container_name, dst_dir_s)
    if contents_only:
        if not is_container_dir_empty(container_name, dst_dir_s):
            raise RuntimeError(f"Directory not empty: {dst_dir_s}")
        src_path = str(src_dir.absolute()).rstrip("/") + "/."
    else:
        src_path = str(src_dir.absolute())
    subprocess.run([
        "docker", "cp", src_path, f"{container_name}:{dst_dir_s}/"
        ], check=True, capture_output=True, text=True)


def copy_file_from_container(
        container_name: str, 
        src_file: str | Path, 
        dst_dir: str | Path,
        *,
        rename: str | None = None,
        mkdir: bool = False,
        overwrite: bool = False
        ) -> None:
    src_file = PurePosixPath(src_file)
    dst_dir = Path(dst_dir)
    if not has_container(container_name):
        raise FileNotFoundError(f"Container not found: {container_name}")
    if not has_container_file(container_name, src_file):
        raise FileNotFoundError(f"File not found: {str(src_file)}")
    target_path = dst_dir / (rename or src_file.name)
    if target_path.exists() and not overwrite:
        raise FileExistsError(f"File already exist: {str(target_path)}")
    if not dst_dir.is_dir():
        if mkdir:
            dst_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Directory not found: {str(dst_dir)}")    
    subprocess.run([
        "docker", "cp", f"{container_name}:{str(src_file)}", str(target_path)
        ], check=True, capture_output=True, text=True)


def copy_dir_from_container(
        container_name: str, 
        src_dir: str | Path, 
        dst_dir: str | Path, 
        *,
        rename: str | None = None,
        mkdir: bool = False,
        contents_only: bool = False
        ) -> None:
    src_dir = PurePosixPath(src_dir)
    dst_dir = Path(dst_dir)
    if rename and contents_only:
        raise ValueError("rename and contents_only cannot be used simultaneously")    
    if not has_container(container_name):
        raise FileNotFoundError(f"Container not exist: {container_name}")
    if not has_container_dir(container_name, src_dir):
        raise FileNotFoundError(f"File not exist: {str(src_dir)}")
    if not dst_dir.is_dir():
        if mkdir:
            dst_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Directory not exist: {str(dst_dir)}")
    if contents_only:
        if any(dst_dir.iterdir()):
            raise RuntimeError(f"Directory not empty: {str(dst_dir)}")
        subprocess.run([
            "docker", "cp", f"{container_name}:{str(src_dir)}/.", str(dst_dir)
        ], check=True, capture_output=True, text=True)
    else:
        target_path = dst_dir / (rename or src_dir.name)
        if target_path.exists():
            raise FileExistsError(f"Directory already exist: {str(target_path)}")
        subprocess.run([
            "docker", "cp", f"{container_name}:{str(src_dir)}", str(target_path)
        ], check=True, capture_output=True, text=True)


def rename_container_dir(
        container_name: str, 
        old_dir_path: str | Path, 
        new_dir_name: str) -> None:
    if "/" in new_dir_name or "\\" in new_dir_name:
        raise ValueError(f"Invalid new name: {new_dir_name}")
    old_dir_path = PurePosixPath(old_dir_path)
    new_dir_path = old_dir_path.parent / new_dir_name
    if old_dir_path == new_dir_path:
        return 
    if not has_container_dir(container_name, str(old_dir_path)):
        raise FileNotFoundError(f"Directory not found: {str(old_dir_path)}")
    if has_container_dir(container_name, str(new_dir_path)):
        raise FileExistsError(f"Directory already exist: {str(new_dir_path)}")
    subprocess.run([
        "docker", "exec", container_name, "mv", str(old_dir_path), str(new_dir_path)
        ], check=True, capture_output=True, text=True)
