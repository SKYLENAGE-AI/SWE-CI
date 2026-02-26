from rich import box
from rich.table import Table
from rich.console import Console
from pathlib import Path

from .utils import read_jsonl, read_csv
from swe_ci.config import CONFIG


def show_results(
        exp_name: str, 
        task_ids: list[str], 
        results: list[dict]
        ) -> None:

    console = Console()
    table = Table(
        title=f"\n📊 [bold cyan]Experiment:[/bold cyan] [bold yellow]{exp_name}[/bold yellow]\n", 
        box=box.DOUBLE_EDGE, 
        header_style="bold magenta",
        show_footer=True
    )
    metrics = list(results[0].keys())
    table.add_column(
        "Task ID", 
        justify="left", 
        style="bright_black", 
        footer="[bold]AVERAGE[/bold]"
    )
    metric_sums = {m: 0.0 for m in metrics}
    for m in metrics:
        table.add_column(m.upper(), justify="right", style="green")
    for tid, res in zip(task_ids, results):
        row_data = [str(tid)]
        for m in metrics:
            val = res.get(m, 0)
            row_data.append(f"{val:.4f}")
            metric_sums[m] += val
        table.add_row(*row_data)
    num_tasks = len(results)
    for i, m in enumerate(metrics):
        avg = metric_sums[m] / num_tasks
        table.columns[i+1].footer = f"[bold yellow]{avg:.4f}[/bold yellow]"
    console.print(table)


def test_based_metrics(
        init_pass: int, 
        target_pass: int, 
        evo_seq: int, 
        seq_len: int | None
        ) -> dict:

    evo_seq = [min(max(0, p), target_pass) for p in evo_seq]
    actual_len = len(evo_seq)
    target_len = seq_len if seq_len is not None else actual_len
    
    if actual_len < target_len:
        fill_value = evo_seq[-1] if actual_len > 0 else init_pass
        evo_seq = evo_seq + [fill_value] * (target_len - actual_len)
    else:
        evo_seq = evo_seq[:target_len]

    total_gap = target_pass - init_pass
    seq_with_init = [init_pass] + evo_seq

    rela_changes = []
    for p in evo_seq:
        if p > init_pass:
            change = (p - init_pass) / total_gap if total_gap > 0 else 1.0
        elif p < init_pass:
            change = (p - init_pass) / init_pass if init_pass > 0 else -1.0
        else:
            change = 0
        rela_changes.append(change)
    m1 = sum([(c + 1) / 2 for c in rela_changes]) / target_len if target_len > 0 else 0.5

    if total_gap > 0:
        m2 = (max(seq_with_init) - init_pass) / total_gap
    else:
        m2 = 1.0
    
    if init_pass > 0:
        m3 = min(seq_with_init) / init_pass
    else:
        m3 = 1.0
    
    m4 = float(max(seq_with_init) == target_pass)

    is_monotonic = True
    for i in range(len(seq_with_init) - 1):
        if seq_with_init[i+1] < seq_with_init[i]:
            is_monotonic = False
            break
    m5 = float(is_monotonic)

    overall = (m1 + m2 + m3 + m4 + m5) / 5
    return {
        "m1": m1, "m2": m2, "m3": m3, "m4": m4, "m5": m5,
        "overall": overall
    }


def token_based_metrics(
        architect_tokens: list[int], 
        programmer_tokens: list[int]
        ) -> dict:
    lens = len(architect_tokens)
    sum_token = sum(architect_tokens) + sum(programmer_tokens)
    avg_token = sum_token / lens
    return {
        "sum_token": sum_token / 1000000, 
        "avg_token": avg_token / 1000000
    }


def epoch_based_metrics():
    pass # TODO


def code_based_metrics():
    pass # TODO


def summarize() -> None:
    metadata_path = Path(CONFIG.save_root_dir) / "metadata" / f"{CONFIG.splitting}.csv"
    task_ids = [t["task_id"] for t in read_csv(metadata_path)]
    exp_path = Path("experiments") / CONFIG.experiment_name
    if not exp_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {str(exp_path)}")
    avaliable_ids, task_results = [], []
    for tid in task_ids:
        iteration_file = exp_path / tid / "iteration.jsonl"
        try:
            results = read_jsonl(iteration_file)
            init_res = results[0]
            evo_res_list = results[1:]
            metrics = test_based_metrics(
                init_pass = init_res["pytest"].get("passed", 0),
                target_pass = init_res["pytest"].get("passed", 0) + init_res["gap"],
                evo_seq = [r["pytest"].get("passed", 0) for r in evo_res_list],
                seq_len = CONFIG.evolve.max_epoch  
                )
            # metrics = metrics | token_based_metrics(
            #     architect_tokens = [r["architect"]["input_tokens"] for r in evo_res_list],
            #     programmer_tokens = [r["programmer"]["input_tokens"] for r in evo_res_list],
            # )
        except Exception as e:
            print(
                f"⚠️ Errror occured when load results from {str(iteration_file)}: {repr(e)}",
                flush=True
                )
        avaliable_ids.append(tid)
        task_results.append(metrics)
    
    print(f"Total tasks: {len(task_ids)}, avaliable: {len(avaliable_ids)}")
    if len(avaliable_ids) > 0:
        show_results(CONFIG.experiment_name, task_ids, task_results)
