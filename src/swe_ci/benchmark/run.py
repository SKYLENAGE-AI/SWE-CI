import fcntl
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

from .utils import *
from .tools import *
from swe_ci.config import CONFIG



def _run(
        task_metadata: dict,
        task_dir: str | Path,
        ):

    task_dir = Path(task_dir)

    # Step 0: Acquire a non-blocking file lock to prevent concurrent execution
    lock_file = open(task_dir / ".lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        return
    try:
        _run_locked(task_metadata, task_dir)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


def _run_locked(
        task_metadata: dict,
        task_dir: Path,
        ):

    # Step 1: Setup task logger
    task_id = task_metadata["task_id"]
    logger = empty_logger(task_id)
    current_dir = task_dir / "current"
    tmp_dir = task_dir / "tmp"
    handler = file_handler(task_dir / "task.log")
    add_handler(logger, handler)

    # Step 2: Skip if task was not initialized or termination condition has been met.
    if not (task_dir / "iteration.jsonl").is_file():
        info = "❌ The task was not initialized."
        logger.error(info)
        raise RuntimeError(info)
    iter_records = read_jsonl(task_dir / "iteration.jsonl")
    current_epoch = len(iter_records) - 1
    logger.info(f"Evolve progress: {current_epoch} / {CONFIG.evolve.max_epoch}")
    if iter_records[-1]["gap"] == 0:
        logger.info(f"✅ All tests passed.")
        return
    if current_epoch >= CONFIG.evolve.max_epoch:
        logger.info("✅ Reached max epochs.")
        return

    # Step 3: Load images and prompts
    try:
        self_path = Path(__file__).resolve()
        task_id = task_metadata['task_id']
        base_image_tag = load_image_from_tar(
            Path(CONFIG.save_root_dir) / "data" / task_id / "image.tar.gz", 
            exist_ok=True)
        image_tag = container_name = uuid.uuid4().hex[:16]
        build_image_from_dockerfile(
            image_tag, 
            self_path.parent / "Dockerfile.agent",
            extra_args = image_extra_args(base_image_tag)
            )
        prompt_file = self_path.parent / "prompt.jinja2"
        architect_prompt = load_prompt(prompt_file, template_args = {'role': 'architect'})
        programmer_prompt = load_prompt(prompt_file,template_args = {'role': 'programmer'})
    except Exception as e:
        info = f"❌ Error occurred when loading resources: {repr(e)}"
        logger.exception(info)
        if has_image(image_tag): 
            remove_image(image_tag)
        raise RuntimeError(info)

    # Step 4: Evolution loop
    try:
        while True:
            # Step 4.1: Clear temporary files
            logger.info("="*20 + f"Epoch {current_epoch + 1}" + "="*20)
            epoch_prefix = f"(Epoch {current_epoch + 1}/{CONFIG.evolve.max_epoch}) "
            shutil.rmtree(tmp_dir, ignore_errors=True)
            (current_dir/"requirement.xml").unlink(missing_ok=True)
            logger.info("(1/7) ✅ Cleaned up temporary files.")

            # Step 4.2: Call architect agent with retry mechanism
            for i in range(1, CONFIG.evolve.architect.max_try+1):
                prefix = f"(2/7) (Attempt {i}/{CONFIG.evolve.architect.max_try}) "
                try:
                    run_container(image_tag, container_name, extra_args=CONTAINER_EXTRA_ARGS)
                    copy_dir_to_container(container_name, current_dir/"code", "/app")
                    copy_dir_to_container(container_name, current_dir/"non-passed", "/app")
                    architect_result = call_cli_agent(
                        container_name, architect_prompt, 
                        timeout=CONFIG.evolve.architect.timeout
                        )
                    copy_file_from_container(container_name, "/app/requirement.xml", current_dir)
                    logger.info(prefix + "✅ The architect agent has generated the requirements.")
                    break
                except Exception as e:
                    info = f"⚠️ Error occurred when calling architect agent: {repr(e)}"
                    logger.exception(prefix + info)
                    if i >= CONFIG.evolve.architect.max_try:
                        raise RuntimeError(
                            epoch_prefix + "❌ Max attempts reached: Fail to call architect agent."
                            )
                finally:
                    if has_container(container_name): 
                        remove_container(container_name)

            # Step 4.3: Call programmer agent with retry mechanism
            for i in range(1, CONFIG.evolve.programmer.max_try+1):
                prefix = f"(3/7) (Attempt {i}/{CONFIG.evolve.programmer.max_try}) "
                try:
                    run_container(image_tag, container_name, extra_args=CONTAINER_EXTRA_ARGS)
                    copy_dir_to_container(container_name, current_dir/"code", "/app")
                    copy_file_to_container(container_name, current_dir/"requirement.xml", "/app")
                    programmer_result = call_cli_agent(
                        container_name, programmer_prompt, 
                        timeout=CONFIG.evolve.programmer.timeout
                        )
                    copy_dir_from_container(container_name, "/app/code", tmp_dir, mkdir=True)
                    logger.info(prefix + "✅ The programmer agent has modified the code.")
                    break
                except Exception as e:
                    info = f"⚠️ Error occurred when calling programmer agent: {repr(e)}"
                    logger.exception(prefix + info)
                    if i >= CONFIG.evolve.programmer.max_try:
                        raise RuntimeError(
                            epoch_prefix + "❌ Max attempts reached: Fail to call programmer agent."
                            )
                finally:
                    if has_container(container_name):
                        remove_container(container_name)
            
            # Step 4.4: Run pytest
            keep_this_epoch = False
            try:
                run_container(image_tag, container_name, extra_args=CONTAINER_EXTRA_ARGS)
                copy_dir_to_container(container_name, tmp_dir/"code", "/app")
                report_path = "/tmp/test_report.json"
                result = run_pytest(container_name, "/app/code", report_path=report_path)
                save_completed_process(result, tmp_dir/"test_result.json")
                returncode = result.returncode
                has_report = has_container_file(container_name, report_path)
                if returncode <= 1 and has_report:
                    copy_file_from_container(container_name, report_path, tmp_dir)
                    keep_this_epoch = True
                    logger.info(f"(4/7) ✅ Ran pytest in programmer modified code. {returncode=}, {has_report=}")
                else:
                    logger.warning(f"(4/7) ⚠️ pytest was not executed correctly. {returncode=}, {has_report=}")
            except subprocess.TimeoutExpired as e:
                logger.warning(f"(4/7) ⚠️ pytest timeout. {repr(e)}")
            except Exception as e:
                info = f"(4/7) ❌ Error occurred when running the pytest: {repr(e)}"
                logger.exception(info)
                raise RuntimeError(epoch_prefix + info)
            finally:
                if has_container(container_name):
                    remove_container(container_name)

            # Step 4.5-4.7: Generate, archive and update
            now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            if keep_this_epoch:
                gap = generate_nonpassed_dir(tmp_dir/"test_report.json", task_dir/"target"/"test_report.json", tmp_dir)
                logger.info("(5/7) ✅ Generated directory 'nonpassed'.")
                current_dir.rename(task_dir / now)
                (task_dir / "tmp").rename(current_dir)
                logger.info("(6/7) ✅ Archived directory 'current', and rename directory 'tmp' to 'current'.")
                update_iteration(
                    gap, task_dir / "iteration.jsonl", current_dir / "test_report.json",
                    addition = {"architect": architect_result, "programmer": programmer_result}
                    )
                logger.info("(7/7) ✅ Updated ineration file.")
            else:
                gap = -1
                logger.info("(5/7) ✅ Skip this step.")
                (task_dir / "tmp").rename(task_dir / now)
                logger.info("(6/7) ✅ Archived directory 'tmp'.")
                update_iteration(
                    -1, task_dir / "iteration.jsonl", None,
                    addition = {"architect": architect_result, "programmer": programmer_result}
                    )
                logger.info("(7/7) ✅ Updated ineration file.")

            # Step 4.6: Exit the loop if the termination condition is met.
            current_epoch += 1
            if current_epoch >= CONFIG.evolve.max_epoch or gap == 0:
                now = datetime.now() + timedelta(seconds=60)
                current_dir.rename(task_dir / now.strftime("%Y-%m-%d-%H-%M-%S"))
                logger.info("Reached the exit condition. Archived directory 'current'.")
                break   
    
    finally:
        if has_image(image_tag):
            remove_image(image_tag)

    remove_handler(logger, handler)



def run_tasks() -> bool:
     
    # Step 1: Initialize directoires and paths
    experiment_dir = Path("experiments") / CONFIG.experiment_name
    experiment_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = Path(CONFIG.save_root_dir) / "metadata" / f"{CONFIG.splitting}.csv"
    metadatas = read_csv(metadata_file)
    num_tasks = len(metadatas)

    # Step 2: Setup main logger
    main_logger = empty_logger("main")
    f_handler = file_handler(experiment_dir / "main.log")
    c_handler = console_handler()
    add_handler(main_logger, f_handler)
    add_handler(main_logger, c_handler)

    # Step 3: Run tasks in multiple processes
    main_logger.info(f"{'='*30} Evolving... {'='*30}")
    current, n_success, n_fail = 0, 0, 0
    with ProcessPoolExecutor(max_workers=CONFIG.evolve.max_workers) as executor:
        future_to_taskid = dict()
        for metadata in metadatas:
            task_id = metadata['task_id']
            future = executor.submit(
                _run, 
                task_metadata = metadata, 
                task_dir = experiment_dir / task_id
                )
            future_to_taskid[future] = task_id
        for future in as_completed(future_to_taskid):
            task_id = future_to_taskid[future]
            current += 1
            try:
                future.result()
                main_logger.info(
                    f"✅ Evolution complete({current}/{num_tasks}). Task ID = {task_id}"
                    )
                n_success += 1
            except Exception as e:
                main_logger.error(
                    f"❌ Evolution failed({current}/{num_tasks}). Task ID = {task_id}"
                    f" | {repr(e)}"
                    )
                n_fail += 1
    main_logger.info(f"Totaling {num_tasks} tasks. {current} executed. {n_success} success, {n_fail} fail.")
    remove_handler(main_logger, f_handler)
    remove_handler(main_logger, c_handler)
    return n_success == num_tasks
