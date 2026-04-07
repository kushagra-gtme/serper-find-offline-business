"""File I/O for run data: JSON, CSV, JSONL."""

import json
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Iterator, Optional
import aiofiles

logger = logging.getLogger("serper")


class FileManager:
    """Manages file operations for search runs."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.runs_path = self.base_path / "runs"
        self.ensure_directories()

    def ensure_directories(self):
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(exist_ok=True)

    def create_run_folder(
        self,
        search_terms: List[str],
        states: List[str],
        cities: Optional[List[str]] = None,
    ) -> tuple[str, Path]:
        """Create a run folder with naming: YYYYMMDD-HHMMSS--<term>--<states>--<scope>"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_term = search_terms[0].replace(" ", "-").replace("/", "-")[:30]
        state_str = "-".join(sorted(s.upper() for s in states[:5]))
        if len(states) > 5:
            state_str += f"-+{len(states) - 5}"

        if cities:
            scope = f"{len(cities)}cities"
        else:
            scope = f"{len(states)}states"

        run_id = f"{timestamp}--{safe_term}--{state_str}--{scope}"
        run_path = self.runs_path / run_id
        run_path.mkdir(exist_ok=True)
        (run_path / "raw").mkdir(exist_ok=True)
        return run_id, run_path

    def get_run_path(self, run_id: str) -> Path:
        return self.runs_path / run_id

    def list_runs(self) -> List[Dict[str, Any]]:
        runs = []
        if not self.runs_path.exists():
            return runs
        for run_dir in sorted(self.runs_path.iterdir(), reverse=True):
            if run_dir.is_dir():
                run_json = run_dir / "run.json"
                if run_json.exists():
                    with open(run_json) as f:
                        config = json.load(f)
                    progress_path = run_dir / "progress.json"
                    if progress_path.exists():
                        with open(progress_path) as f:
                            config["progress"] = json.load(f)
                    runs.append(config)
        return runs

    async def write_json(self, path: Path, data: Dict[str, Any]):
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    def read_json(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")
        except FileNotFoundError:
            raise ValueError(f"File not found: {path}")

    async def append_jsonl(self, path: Path, data: Any):
        async with aiofiles.open(path, "a") as f:
            await f.write(json.dumps(data) + "\n")

    def stream_jsonl(self, path: Path) -> Iterator[Dict[str, Any]]:
        with open(path) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    async def write_csv(self, path: Path, headers: List[str], rows: List[List[str]]):
        async with aiofiles.open(path, "w", newline="") as f:
            await f.write(",".join(headers) + "\n")
            for row in rows:
                await f.write(",".join(_escape_csv(field) for field in row) + "\n")

    async def append_csv_rows(self, path: Path, headers: List[str], rows: List[List[str]]):
        file_exists = path.exists()
        async with aiofiles.open(path, "a", newline="") as f:
            if not file_exists:
                await f.write(",".join(headers) + "\n")
            for row in rows:
                await f.write(",".join(_escape_csv(field) for field in row) + "\n")

    def read_csv(self, path: Path) -> tuple[List[str], List[List[str]]]:
        try:
            with open(path, newline="") as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)
            return headers, rows
        except FileNotFoundError:
            raise ValueError(f"CSV file not found: {path}")
        except StopIteration:
            raise ValueError(f"CSV file is empty: {path}")

    def count_csv_rows(self, path: Path) -> int:
        if not path.exists():
            return 0
        with open(path) as f:
            return sum(1 for _ in f) - 1  # exclude header


def _escape_csv(field: str) -> str:
    """Escape a CSV field value per RFC 4180.

    Wraps the field in double quotes if it contains commas, double quotes,
    or newlines. Inner double quotes are escaped by doubling them.
    """
    if "," in field or '"' in field or "\n" in field:
        return '"' + field.replace('"', '""') + '"'
    return field
