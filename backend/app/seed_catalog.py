from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SEED_DATA_DIR = Path(__file__).with_name("seed_data")

CATALOGS = [
    {
        "source": "computational-thinking.txt",
        "room_code": "CT-MID",
        "title": "컴퓨팅 사고 중간고사",
        "course": "컴퓨팅 사고",
        "professor": "신찬수",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 120,
        "starts_at": datetime.fromisoformat("2026-06-15T09:00:00+09:00"),
    },
    {
        "source": "data-structures.txt",
        "room_code": "DS-MID",
        "title": "자료구조 중간고사",
        "course": "자료구조",
        "professor": "신찬수",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 120,
        "starts_at": datetime.fromisoformat("2026-06-17T09:00:00+09:00"),
    },
    {
        "source": "algorithms.txt",
        "room_code": "ALG-MID",
        "title": "알고리즘 중간고사",
        "course": "알고리즘",
        "professor": "신찬수",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 120,
        "starts_at": datetime.fromisoformat("2026-06-19T09:00:00+09:00"),
    },
]

PROBLEM_HEADING = re.compile(r"^# \*\*.+? 문제 \d+\*\*\s*$", re.MULTILINE)
SECTION_HEADING = re.compile(r"^## \*\*(.*?)\*\*\s*$", re.MULTILINE)
FENCED_CODE = re.compile(r"```(?:python)?\s*\n?(.*?)```", re.DOTALL)
HIDDEN_CASES_PATH = SEED_DATA_DIR / "hidden-cases.json"


def build_seed_exams() -> list[dict[str, Any]]:
    hidden_cases = json.loads(HIDDEN_CASES_PATH.read_text(encoding="utf-8"))
    exams: list[dict[str, Any]] = []
    for catalog in CATALOGS:
        source = SEED_DATA_DIR / str(catalog["source"])
        problems = parse_problem_catalog(source.read_text(encoding="utf-8"))
        if len(problems) != 10:
            raise RuntimeError(f"{source.name} must contain exactly 10 problems")
        for problem in problems:
            problem["hidden_cases"] = hidden_cases.get(problem["title"], [])
            if len(problem["hidden_cases"]) < 3:
                raise RuntimeError(f"{problem['title']} must contain at least 3 hidden cases")

        exam = {key: value for key, value in catalog.items() if key != "source"}
        exam["problems"] = problems
        exams.append(exam)
    return exams


def parse_problem_catalog(text: str) -> list[dict[str, Any]]:
    matches = list(PROBLEM_HEADING.finditer(text))
    return [
        _parse_problem(text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        for index, match in enumerate(matches)
    ]


def _parse_problem(block: str) -> dict[str, Any]:
    sections = _sections(block)
    title_heading = next(
        (heading for heading in sections if heading.startswith("문제명:")),
        None,
    )
    if title_heading is None:
        raise RuntimeError("Problem title is missing")

    title = title_heading.split(":", 1)[1].strip()
    difficulty = _plain_text(sections.get("난이도", ""))
    core_heading = next((heading for heading in sections if heading.startswith("핵심 ")), "")
    core = _plain_text(sections.get(core_heading, ""))
    sample_input = _code_block(sections.get("예시 입력", ""))
    sample_output = _code_block(sections.get("예시 출력", ""))
    reference_solution = _code_block(sections.get("정답 코드", ""))
    if not sample_input or not sample_output or not reference_solution:
        raise RuntimeError(f"{title} is missing sample data or a reference solution")

    level = _level(difficulty)
    return {
        "title": title,
        "level": level,
        "points": 10,
        "description": [
            *([f"핵심 개념: {core}"] if core else []),
            *_plain_lines(sections.get("문제 설명", "")),
        ],
        "input_description": _plain_text(sections.get("입력", "")),
        "output_description": _plain_text(sections.get("출력", "")),
        "constraints": _plain_lines(sections.get("제한", "")),
        "samples": [{"input": sample_input, "output": sample_output}],
        "starter_code": f"# {title}\n# 여기에 코드를 작성하세요.\n",
        "reference_solution": f"{reference_solution}\n",
        "time_limit_ms": 2000 if level == "Easy" else 3000 if level == "Medium" else 5000,
        "memory_limit_mb": 128 if level == "Easy" else 256,
        "hidden_cases": [],
    }


def _sections(block: str) -> dict[str, str]:
    matches = list(SECTION_HEADING.finditer(block))
    return {
        match.group(1).strip(): block[
            match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(block)
        ].strip()
        for index, match in enumerate(matches)
    }


def _plain_text(value: str) -> str:
    return " ".join(_plain_lines(value))


def _plain_lines(value: str) -> list[str]:
    lines: list[str] = []
    for raw in value.splitlines():
        line = raw.strip()
        if not line or line.startswith("```") or line == "---":
            continue
        line = line.replace("**", "").replace("`", "").strip()
        if line.startswith("- "):
            line = line[2:].strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            line = " · ".join(cells)
        if line:
            lines.append(line)
    return lines


def _code_block(value: str) -> str:
    match = FENCED_CODE.search(value)
    return match.group(1).strip() if match else ""


def _level(difficulty: str) -> str:
    if difficulty == "하":
        return "Easy"
    if difficulty == "상":
        return "Hard"
    return "Medium"
