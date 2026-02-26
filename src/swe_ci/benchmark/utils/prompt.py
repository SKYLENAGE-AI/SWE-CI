from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def load_prompt(
        template_path: str | Path,
        template_args: dict | None
        ) -> str:
    args = f"{template_path=}, {template_args=}"
    template_path = Path(template_path)
    if not template_path.is_file():
        raise FileNotFoundError(f"File not found: {template_path}")
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined, 
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)
    prompt = template.render(**(template_args or {}))
    return prompt
