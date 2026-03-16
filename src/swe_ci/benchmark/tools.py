import json
import uuid
import shutil
import hashlib
import subprocess
from pathlib import Path
from subprocess import CompletedProcess

from .utils import *
from .agents import *
from swe_ci.config import CONFIG



def container_extra_args() -> list[str]:
    extra_args = []
    if CONFIG.docker.cpus != "":
        extra_args.extend(["--cpus", str(CONFIG.docker.cpus)])
    if CONFIG.docker.memory != "":
        extra_args.extend(["--memory", CONFIG.docker.memory])
        extra_args.extend(["--memory-swap", CONFIG.docker.memory])
    if CONFIG.docker.memory_reservation != "":
        extra_args.extend(["--memory-reservation", CONFIG.docker.memory_reservation])
    if CONFIG.docker.read_bps != "":
        extra_args.extend(
            ["--device-read-bps", f"{CONFIG.docker.storage_disk}:{CONFIG.docker.read_bps}"]
            )
    if CONFIG.docker.write_bps != "":
        extra_args.extend(
            ["--device-write-bps", f"{CONFIG.docker.storage_disk}:{CONFIG.docker.write_bps}"]
            )
    return extra_args


CONTAINER_EXTRA_ARGS = container_extra_args()


def image_extra_args(base_image_tag: str) -> list[str]:
    return [
        "--build-arg", f"BASE_IMAGE={base_image_tag}",
        "--build-arg", f"NODE_VERSION={CONFIG.agent.node_version}",
        "--build-arg", f"AGENT_NPM_PKG={CONFIG.agent.npm_pkg}",
        "--build-arg", f"AGENT_BIN={CONFIG.agent.npm_bin}"
        ]


def run_pytest(
        container_name: str, 
        repo_dir: str | Path,
        *,
        report_path: str | Path = "/tmp/test_report.json",
        ) -> subprocess.CompletedProcess:
    subprocess.run([
        "docker", "exec", container_name, "bash", "-c", f"rm -rf {report_path}"
        ], check=False)
    pytest_cmd = [
        "docker", "exec", "-w", repo_dir, "-e", "PYTHONPATH=src:.", container_name,
        "python", "-m", "pytest", "tests",
        "--color=no", "--tb=short", "--disable-warnings", "-rfE", f"--rootdir={repo_dir}",
        "--json-report", f"--json-report-file={report_path}"
    ]
    result = subprocess.run(
        pytest_cmd, capture_output=True, text=True, timeout=CONFIG.pytest.timeout
    )
    return result


def cold_test(
        base_image_tar: str | Path,
        agent_dockerfile: str | Path,
        repo_dir: str | Path,
        report_path: str | Path,
        ) -> CompletedProcess:
    base_image_tag = load_image_from_tar(base_image_tar, exist_ok=True)
    image_tag = container_name = uuid.uuid4().hex[:16]
    container_report = "/tmp/test_report.json"
    build_image_from_dockerfile(
        image_tag, str(agent_dockerfile),
        extra_args = image_extra_args(base_image_tag)
        )
    run_container(
        image_tag = image_tag, 
        container_name = container_name, 
        extra_args = CONTAINER_EXTRA_ARGS,
        overwrite=True
        )
    copy_dir_to_container(container_name, repo_dir, "/app", contents_only=False)
    rename_container_dir(container_name, f"/app/{Path(repo_dir).name}", "codes")
    result = run_pytest(container_name, "/app/codes", report_path=container_report)
    report_path = Path(report_path)
    copy_file_from_container(container_name, container_report, report_path.parent, rename=report_path.name)
    if has_container(container_name):
        remove_container(container_name)
    if has_image(image_tag):
        remove_image(image_tag)
    return result


def safe_name(node_id: str) -> str:
    safe_name = "".join(c if c.isalnum() or c == '.' else '_' for c in node_id)
    if len(safe_name) > 100:
        hash_suffix = hashlib.sha256(node_id.encode('utf-8')).hexdigest()[:12]
        safe_name = f"{safe_name[:100]}_{hash_suffix}.json"
    return safe_name


def generate_nonpassed_dir(
        current_report: str | Path,
        target_report: str | Path,
        output_root: str | Path
        ) -> int:

    current = json.loads(Path(current_report).read_text(encoding="utf-8"))
    target = json.loads(Path(target_report).read_text(encoding="utf-8"))
    
    current_passed_ids = set([t['nodeid'] for t in current['tests'] if t['outcome'] == 'passed'])
    target_passed_ids = set([t['nodeid'] for t in target['tests'] if t['outcome'] == 'passed'])
    nonpassed_ids = target_passed_ids - current_passed_ids
    
    current_tests = {t['nodeid']: t for t in current['tests']}
    nonpassed_dir = Path(output_root) / "non-passed"
    shutil.rmtree(nonpassed_dir, ignore_errors=True)
    nonpassed_dir.mkdir(parents=True, exist_ok=True)
    with (nonpassed_dir / "summary.jsonl").open('w', encoding='utf-8') as f:
        for node_id in nonpassed_ids:
            if node_id in current_tests:
                stage, reason = "", ""
                test_node = current_tests[node_id]
                detail_path = nonpassed_dir / safe_name(node_id)
                for s in ['setup', 'call', 'teardown']:
                    if s in test_node and 'longrepr' in test_node[s]:
                        reason = "Reason: " + test_node[s]['longrepr'].strip().split('\n')[-1]
                        stage = " at " + s + " stage"
                        break
                f.write(json.dumps({
                    'test': node_id,
                    'description': f"Test {test_node['outcome']}{stage}. {reason}. Detailed traceback is recorded in {str(detail_path)}"
                    }, ensure_ascii=False) + '\n')
                with detail_path.open('w', encoding='utf-8') as d:
                    json.dump(test_node, d, ensure_ascii=False, indent=4)
            else:
                f.write(json.dumps({
                    'test': node_id,
                    'description': f"This test was not properly collected or executed in the current run, so no detailed traceback is available. However, it was recorded as 'passed' in the target report."
                }, ensure_ascii=False) + '\n')
    return len(nonpassed_ids)


def update_iteration(
        gap: int,
        iteration_file: str | Path,
        test_report: str | Path | None,
        addition: dict | None = None
        ) -> None:
    if test_report is None:
        summary = {}
    else:
        report = json.loads(Path(test_report).read_text(encoding='utf-8'))
        summary = report.get("summary", {})
    record = {"gap": gap, "pytest": summary}
    record = record | addition if addition else record
    context = json.dumps(record, ensure_ascii=False) + '\n'
    with open(Path(iteration_file), 'a', encoding='utf-8') as f:
        f.write(context)



def call_cli_agent(
        container_name: str, 
        prompt: str, 
        *,
        work_dir: str = "/app",
        timeout:int
        ) -> dict:
    agent = CONFIG.agent_name
    func_map = {
        "iflow": call_iflow,
        "claude": call_claude
    }
    if agent not in func_map:
        raise NotImplementedError(f"CONFIG.agent = {agent}")
    agent_func = func_map[agent]
    return agent_func(container_name, prompt, work_dir=work_dir, timeout=timeout)
