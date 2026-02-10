from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class DiabetesTrackerStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as infile:
            return json.load(infile)

    def save(self, payload: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as outfile:
            json.dump(payload, outfile, indent=2)
