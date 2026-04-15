import json
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from .utils import *
from .tools import *
from swe_ci.config import CONFIG


def _init(        
        task_metadata: dict, 
        data_dir: str | Path, 
        task_dir: str | Path
        ):
    
    # Setup task logger
    task_id = task_metadata["task_id"]
    logger = empty_logger(task_id)
    handler = file_handler(Path(task_dir) / "task.log")
    add_handler(logger, handler)
    logger.info("="*20 + f"task id: {task_id}" + "="*20)
    logger.info(f"Task metadata:\n{task_metadata}")

    # Skip if not downloaded or already initialized.
    data_dir, task_dir = Path(data_dir), Path(task_dir)
    self_path = Path(__file__).resolve()
    logger.info(f"Data source: {data_dir}")
    logger.info(f"Task directory: {task_dir}")
    if (task_dir / "iteration.jsonl").is_file():
        logger.info("✅ File iteration.jsonl found in task directory, skip initialization.")
        return
    if not (data_dir / "code.zip").is_file() or not (data_dir / "image.tar.gz").is_file():
        info = "❌ The data has not yet been downloaded."
        logger.error(info)
        raise RuntimeError(info)
    logger.info("(0/5) Initializing task directory...")
    for item in task_dir.iterdir():
        if item.name == "task.log": continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    
    # Initialize task directories
    current_dir = task_dir / "current"
    target_dir = task_dir / "target"
    try:
        current_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        unzip(data_dir / "code.zip", current_dir / "code")
        shutil.copytree(current_dir / "code", target_dir / "code")
        checkout(current_dir / "code", task_metadata["current_sha"])
        checkout(target_dir / "code", task_metadata["target_sha"])
        remove_pattern_files(current_dir / "code", [".git*", "test", "tests"])
        remove_pattern_files(target_dir / "code", [".git*", "test"])
        shutil.copytree(target_dir / "code" / "tests", current_dir / "code" / "tests")
        logger.info("(1/5) ✅ Extracted the 'current' and 'target' directories.")
    except Exception as e:
        info = f"(1/5) ❌ Error occurred when extracting directories: {repr(e)}"
        logger.exception(info)
        raise RuntimeError(info)

    # Run pytest in current codes
    try:
        curr_result = cold_test(
            base_image_tar = data_dir / "image.tar.gz", 
            agent_dockerfile = CONFIG.agent.dockerfile,
            repo_dir = current_dir / "code",
            report_path = current_dir / "test_report.json",
        )
        save_completed_process(curr_result, current_dir / "test_result.json")
        if curr_result.returncode > 1:
            info = "(2/5) ❌ pytest failed in directory 'current': returncode > 1"
            logger.error(info + f"\nreturncode={curr_result.returncode}, stderr={curr_result.stderr}")
            raise RuntimeError(info)
        report = json.loads((current_dir / "test_report.json").read_text("utf-8"))
        current_passed = [n["nodeid"] for n in report["tests"] if n["outcome"] == "passed"]
    except Exception as e:
        info = f"(2/5) ❌ Error occurred when running pytest in directory 'current': {repr(e)}"
        logger.exception(info)
        raise RuntimeError(info)
    else:
        logger.info("(2/5) ✅ Ran pytest in directory 'current'.")

    # Run pytest in target codes
    try:
        target_result = cold_test(
            base_image_tar = data_dir / "image.tar.gz",
            agent_dockerfile = CONFIG.agent.dockerfile,
            repo_dir = target_dir / "code",
            report_path = target_dir / "test_report.json"
        )
        save_completed_process(target_result, target_dir / "test_result.json")
        if target_result.returncode > 1:
            info = "(3/5) ❌ pytest failed in directory 'target': returncode > 1"
            logger.error(info + f"\nreturncode={target_result.returncode}, stderr={target_result.stderr}")
            raise RuntimeError(info)
        report = json.loads((target_dir / "test_report.json").read_text("utf-8"))
        target_passed = [n["nodeid"] for n in report["tests"] if n["outcome"] == "passed"]
    except Exception as e:
        info = f"(3/5) ❌ Error occurred when running pytest in directory 'target': {repr(e)}"
        logger.exception(info)
        raise RuntimeError(info)
    else:
        logger.info("(3/5) ✅ Ran pytest in directory 'target'.")

    expected_gap = int(task_metadata["test_gap"])
    gap = len(set(target_passed) - set(current_passed))
    if gap != expected_gap:
        logger.warning(f"⚠️ Expected gap = {expected_gap}, but got {gap}.")

    # Generate non-passed directory by comparing two reports
    try:
        gap = generate_nonpassed_dir(current_dir / "test_report.json", target_dir / "test_report.json", current_dir)    
    except Exception as e:
        info = f"(4/5) ❌ Error occurred when generating directory 'nonpassed': {repr(e)}"
        logger.exception(info)
        raise RuntimeError(info)
    else:
        logger.info("(4/5) ✅ Generated directory 'nonpassed'.")

    update_iteration(
        gap, task_dir / "iteration.jsonl", current_dir / "test_report.json"
        )
    logger.info("(5/5) ✅ Updated iteration file.")
    logger.info("✅ Initialization Finish.")
    remove_handler(logger, handler)


def init_tasks() -> bool:
    
    # Step 1: Initialize directoires and paths
    experiment_dir = Path("experiments") / CONFIG.experiment_name
    experiment_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = Path(CONFIG.save_root_dir) / "metadata" / f"{CONFIG.splitting}.csv"
    data_dir = Path(CONFIG.save_root_dir) / "data"
    metadatas = read_csv(metadata_file)
    num_tasks = len(metadatas)

    # Step 2: Setup main logger
    main_logger = empty_logger("main")
    f_handler = file_handler(experiment_dir / "main.log")
    c_handler = console_handler()
    add_handler(main_logger, f_handler)
    add_handler(main_logger, c_handler)

    # Step 3: Initialize tasks in multiple processes
    main_logger.info(f"{'='*30} Initializing tasks... {'='*30}")
    current, n_success, n_fail = 0, 0, 0
    with ProcessPoolExecutor(max_workers=CONFIG.init.max_workers) as executor:
        future_to_taskid = dict()
        for metadata in metadatas:
            task_id = metadata['task_id']
            future = executor.submit(
                _init, 
                task_metadata = metadata, 
                data_dir = data_dir / task_id, 
                task_dir = experiment_dir / task_id,
                )
            future_to_taskid[future] = task_id
        for future in as_completed(future_to_taskid):
            task_id = future_to_taskid[future]
            current += 1
            try:
                future.result()
                main_logger.info(
                    f"✅ Initialize successful({current}/{num_tasks}). Task ID = {task_id}"
                    )
                n_success += 1
            except Exception as e:
                main_logger.error(
                    f"❌ Initialize failed({current}/{num_tasks}). Task ID = {task_id}"
                    f" | {repr(e)}"
                    )
                n_fail += 1

    main_logger.info(f"Totaling {num_tasks} tasks. {current} executed. {n_success} success, {n_fail} fail.")
    remove_handler(main_logger, f_handler)
    remove_handler(main_logger, c_handler)
    return n_success == num_tasks
