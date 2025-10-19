from __future__ import annotations

from pathlib import Path
from typing import Dict


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fill_prompt(template: str, replacements: Dict[str, str]) -> str:
    prompt = template
    for key, value in replacements.items():
        placeholder = f"{{{{{key}}}}}"
        prompt = prompt.replace(placeholder, value)
    return prompt
