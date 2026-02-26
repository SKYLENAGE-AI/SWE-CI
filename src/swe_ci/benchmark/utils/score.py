import io
import re
from pathlib import Path
from pylint.lint import Run
from pylint.reporters.text import TextReporter
from radon.metrics import mi_visit
from radon.raw import analyze as raw_metrics


def pylint_score(
        repo_path: str | Path, 
        exclude: list[str] | None = None
        ) -> float:
    repo_path = Path(repo_path)
    try:
        args = [str(repo_path), "--rcfile=", "--persistent=n", "--exit-zero"]
        if exclude:
            patterns = []
            for item in exclude:
                escaped_path = re.escape(str(repo_path / item))
                patterns.append(f"^{escaped_path}(/.*|$)")
            args.append(f"--ignore-paths={','.join(patterns)}")
        results = Run(
            args, reporter=TextReporter(io.StringIO()), 
            exit=False
        )
        stats = getattr(results.linter, 'stats', None)
        return getattr(stats, 'global_note', -1) if stats else -1
    except Exception as e:
        return -1


def mi_score(
        repo_path: str | Path, 
        exclude: list[str] | None = None
        ) -> float:
    total_mi, total_loc = 0, 0
    repo_path_obj = Path(repo_path)
    exclude_set = set(exclude) if exclude else set()
    for path in repo_path_obj.rglob('*.py'):
        try:
            rel_path = path.relative_to(repo_path_obj)
            if rel_path.parts and rel_path.parts[0] in exclude_set:
                continue
            context = path.read_text(encoding='utf-8')
            loc = raw_metrics(context).sloc            
            total_loc += loc
            total_mi += loc * mi_visit(context, multi=True)
        except Exception:
            continue
    return total_mi / total_loc if total_loc else -1
