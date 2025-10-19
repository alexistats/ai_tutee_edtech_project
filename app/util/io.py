from __future__ import annotations

import json
from typing import Any, Dict, Iterable

import yaml

from pathlib import Path


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_logdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            json.dump(record, handle)
            handle.write("\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
