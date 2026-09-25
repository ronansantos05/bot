from __future__ import annotations

import json
from pathlib import Path


class State:
    """Lembra o que já foi notificado (e a que preço) entre execuções."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.seen: dict[str, float | None] = {}
        if self.path.exists():
            self.seen = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def empty(self) -> bool:
        return not self.seen

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.seen, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)
