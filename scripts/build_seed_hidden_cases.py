from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.seed_catalog import parse_problem_catalog
from backend.app.seed_hidden_inputs import HIDDEN_CASE_INPUTS


SEED_DATA_DIR = ROOT / "backend" / "app" / "seed_data"
OUTPUT = SEED_DATA_DIR / "hidden-cases.json"


def normalize_output(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines()).strip()


def main() -> None:
    problems = {}
    for path in sorted(SEED_DATA_DIR.glob("*.txt")):
        for problem in parse_problem_catalog(path.read_text(encoding="utf-8")):
            problems[problem["title"]] = problem

    missing = sorted(set(problems) - set(HIDDEN_CASE_INPUTS))
    unknown = sorted(set(HIDDEN_CASE_INPUTS) - set(problems))
    if missing or unknown:
        raise RuntimeError(f"Hidden case title mismatch: missing={missing}, unknown={unknown}")

    result: dict[str, list[dict[str, str]]] = {}
    for title, problem in problems.items():
        cases = []
        for input_data in HIDDEN_CASE_INPUTS[title]:
            completed = subprocess.run(
                [sys.executable, "-c", problem["reference_solution"]],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"{title} reference solution failed: {completed.stderr}")
            cases.append(
                {
                    "input": input_data,
                    "output": normalize_output(completed.stdout),
                }
            )
        result[title] = cases

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"generated {sum(len(cases) for cases in result.values())} hidden cases")


if __name__ == "__main__":
    main()
