import re
import os
import sys
import json
import tomlkit
import argparse
import platform
import subprocess
from pathlib import Path
from pprint import pprint
from types import SimpleNamespace
from jsonargparse import ArgumentParser



def get_docker_storage_disk() -> str:
    system = platform.system().lower()
    if platform.system().lower() != "linux":
        raise NotImplementedError(system)

    try:
        docker_root = subprocess.check_output(
            ["docker", "info", "-f", "{{.DockerRootDir}}"], 
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        docker_root = "/var/lib/docker"
    if not os.path.exists(docker_root):
        docker_root = "/"

    try:
        partition_path = subprocess.check_output(
            ["df", "--output=source", docker_root], 
            text=True
        ).strip().splitlines()[-1]
        try:
            parent_node = subprocess.check_output(
                ["lsblk", "-no", "pkname", partition_path], 
                text=True
            ).strip()       
            if parent_node:
                return os.path.join("/dev", parent_node)
            else:
                return partition_path      
        except Exception:
            if "nvme" in partition_path:
                return re.sub(r'p\d+$', '', partition_path)
            else:
                return re.sub(r'\d+$', '', partition_path)
    except subprocess.CalledProcessError as e:
        print(f"Can not identify Docker storage device: {e}")
        sys.exit(1)


def redact_pprint(x, keys=("api_key", "hf_token"), repl="***") -> None:
    print(f"="*25 + " Configuration "+ "="*25, flush=True)
    keys = {k.lower() for k in keys}
    def walk(v):
        if isinstance(v, SimpleNamespace):
            return walk(vars(v))
        if isinstance(v, dict):
            return {k: (repl if k.lower() in keys else walk(val)) for k, val in v.items()}
        if isinstance(v, (list, tuple)):
            return type(v)(walk(i) for i in v)
        return v
    pprint(walk(x))
    print(f"="*65, flush=True)


def load_config() -> SimpleNamespace:

    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config_file", default="config.toml", type=str)
    pre_args, unknown = pre_parser.parse_known_args()
    config_file_path = Path(__file__).resolve().parents[2] / pre_args.config_file
    
    if not config_file_path.exists():
        print(f"File doesn't exist: {config_file_path}", flush=True)
        sys.exit(1)
    
    parser = ArgumentParser()
    parser.add_argument(f"--config_file", default="config.toml", type=str, help="configuration file name")

    def add_arguments_recursive(data, prefix=""):
        for key, value in data.items():
            full_key = f"{prefix}{key}"
            item = data.item(key)
            help_text = item.trivia.comment.strip("# ") if hasattr(item, "trivia") else " "
            if isinstance(value, dict):
                add_arguments_recursive(value, prefix=f"{full_key}.")
            else:
                val = value.unwrap() if hasattr(value, "unwrap") else value
                val_type = type(val)
                parser.add_argument(f"--{full_key}", default=val, type=val_type, help=help_text)

    doc = tomlkit.parse(config_file_path.read_text("utf-8"))
    add_arguments_recursive(doc) 
    cfg = parser.parse_args()

    if not hasattr(cfg, "docker"): 
        cfg.docker = SimpleNamespace(storage_disk="")
    if cfg.docker.storage_disk == "":
        cfg.docker.storage_disk = get_docker_storage_disk()
    if cfg.agent_name == "iflow":
        if not hasattr(cfg, "agent"): cfg.agent = SimpleNamespace()
        cfg.agent.node_version = getattr(cfg.agent, "node_version", None) or "22.11.0"
        cfg.agent.npm_pkg = getattr(cfg.agent, "npm_pkg", None) or "@iflow-ai/iflow-cli"
        cfg.agent.npm_bin = getattr(cfg.agent, "npm_bin", None) or "iflow"
        if not hasattr(cfg, "iflow") or getattr(cfg.iflow, "auth_type", "") not in ["iflow", "openai-compatible"]:
            print(f"The authentication method for iflow must be 'iflow' or 'openai-compatible'.", flush=True)
            sys.exit(1)
    elif cfg.agent_name == "claude":
        if not hasattr(cfg, "agent"): cfg.agent = SimpleNamespace()
        cfg.agent.node_version = getattr(cfg.agent, "node_version", None) or "22.11.0"
        cfg.agent.npm_pkg = getattr(cfg.agent, "npm_pkg", None) or "@anthropic-ai/claude-code"
        cfg.agent.npm_bin = getattr(cfg.agent, "npm_bin", None) or "claude"
    else:
        print(f"Unsupported agent: {cfg.agent_name}", flush=True)
        sys.exit(1)

    return json.loads(
        json.dumps(cfg.as_dict()), 
        object_hook=lambda d: SimpleNamespace(**d)
    )


CONFIG = load_config()
redact_pprint(CONFIG)
