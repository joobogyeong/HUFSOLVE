from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from .models import Exam, Problem, Testcase


def _starter(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


SEED_EXAMS = [
    {
        "room_code": "HUF-2026",
        "title": "클라우드 컴퓨팅 실습 평가",
        "course": "Cloud Computing",
        "professor": "김하늘",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 75,
        "starts_at": datetime.fromisoformat("2026-06-03T09:00:00+09:00"),
        "problems": [
            {
                "title": "A+B 자동 채점",
                "level": "Easy",
                "points": 15,
                "description": [
                    "두 정수 A와 B를 입력받아 합을 출력하세요.",
                    "표준 입력으로 주어진 값을 읽고, 정답은 표준 출력으로만 출력해야 합니다.",
                ],
                "input_description": "첫째 줄에 정수 A와 B가 공백으로 구분되어 주어집니다.",
                "output_description": "A+B의 값을 한 줄에 출력합니다.",
                "constraints": ["-1,000 <= A, B <= 1,000", "불필요한 문장은 출력하지 않습니다."],
                "samples": [
                    {"input": "1 2", "output": "3"},
                    {"input": "-4 9", "output": "5"},
                ],
                "starter_code": _starter(
                    ["a, b = map(int, input().split())", "# TODO: 두 수의 합을 출력하세요."]
                ),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "1000 -7", "output": "993"},
                    {"input": "0 0", "output": "0"},
                ],
            },
            {
                "title": "최댓값 찾기",
                "level": "Easy",
                "points": 15,
                "description": [
                    "정수 배열이 주어졌을 때 가장 큰 값을 출력하세요.",
                    "배열의 길이는 첫 줄에 주어지고, 둘째 줄에 배열 원소가 주어집니다.",
                ],
                "input_description": "첫째 줄에 N, 둘째 줄에 N개의 정수가 주어집니다.",
                "output_description": "배열에서 가장 큰 정수를 출력합니다.",
                "constraints": ["1 <= N <= 100,000", "-10^9 <= 각 원소 <= 10^9"],
                "samples": [{"input": "5\n3 1 9 2 7", "output": "9"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "arr = list(map(int, input().split()))",
                        "# TODO: 최댓값을 출력하세요.",
                    ]
                ),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "1\n-10", "output": "-10"},
                    {"input": "4\n4 4 4 4", "output": "4"},
                ],
            },
            {
                "title": "요청 로그 집계",
                "level": "Medium",
                "points": 20,
                "description": [
                    "API 서버 로그에서 성공 응답의 개수를 집계하세요.",
                    "각 로그는 HTTP status code 하나로 표현되며, 200 이상 300 미만이면 성공입니다.",
                ],
                "input_description": "첫째 줄에 로그 수 N, 다음 N줄에 status code가 주어집니다.",
                "output_description": "성공 응답의 개수를 출력합니다.",
                "constraints": ["1 <= N <= 200,000", "100 <= status code <= 599"],
                "samples": [{"input": "6\n200\n201\n404\n500\n204\n302", "output": "3"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "count = 0",
                        "for _ in range(n):",
                        "    status = int(input())",
                        "    # TODO: 성공 응답을 세어보세요.",
                        "print(count)",
                    ]
                ),
                "time_limit_ms": 3000,
                "memory_limit_mb": 256,
                "hidden_cases": [
                    {"input": "3\n100\n199\n300", "output": "0"},
                    {"input": "4\n299\n200\n250\n500", "output": "3"},
                ],
            },
        ],
    },
    {
        "room_code": "ALG-MID",
        "title": "알고리즘 문제 해결 중간평가",
        "course": "Algorithm",
        "professor": "이서준",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 90,
        "starts_at": datetime.fromisoformat("2026-06-05T13:30:00+09:00"),
        "problems": [
            {
                "title": "올바른 괄호",
                "level": "Easy",
                "points": 15,
                "description": [
                    "괄호 문자열이 올바른지 판별하세요.",
                    "열린 괄호는 반드시 나중에 등장하는 닫힌 괄호와 짝을 이루어야 합니다.",
                ],
                "input_description": "한 줄에 괄호 문자열 S가 주어집니다.",
                "output_description": "올바른 괄호 문자열이면 YES, 아니면 NO를 출력합니다.",
                "constraints": ["1 <= |S| <= 200,000", "S는 '('와 ')'로만 구성됩니다."],
                "samples": [
                    {"input": "(()())", "output": "YES"},
                    {"input": "())(", "output": "NO"},
                ],
                "starter_code": _starter(["s = input().strip()", "# TODO: 올바른 괄호인지 출력하세요."]),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "(", "output": "NO"},
                    {"input": "()()()", "output": "YES"},
                ],
            },
            {
                "title": "회의실 배정",
                "level": "Medium",
                "points": 20,
                "description": [
                    "시작 시각과 종료 시각이 주어진 회의 중 겹치지 않게 선택할 수 있는 최대 개수를 구하세요.",
                    "한 회의가 끝나는 시각에 다른 회의를 바로 시작할 수 있습니다.",
                ],
                "input_description": "첫째 줄에 N, 다음 N줄에 시작 시각과 종료 시각이 주어집니다.",
                "output_description": "선택 가능한 회의의 최대 개수를 출력합니다.",
                "constraints": ["1 <= N <= 100,000", "0 <= 시작 < 종료 <= 10^9"],
                "samples": [{"input": "4\n1 3\n2 4\n3 5\n0 7", "output": "2"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "meetings = [tuple(map(int, input().split())) for _ in range(n)]",
                        "# TODO: 최대 회의 수를 출력하세요.",
                    ]
                ),
                "time_limit_ms": 3000,
                "memory_limit_mb": 256,
                "hidden_cases": [
                    {"input": "3\n1 2\n2 3\n3 4", "output": "3"},
                    {"input": "2\n1 10\n2 3", "output": "1"},
                ],
            },
        ],
    },
]


def seed_database(db: Session) -> None:
    if db.query(Exam).first() is not None:
        return

    for exam_data in SEED_EXAMS:
        problems = exam_data["problems"]
        exam_fields = {key: value for key, value in exam_data.items() if key != "problems"}
        exam = Exam(**exam_fields)
        db.add(exam)
        db.flush()

        for problem_data in problems:
            hidden_cases = problem_data["hidden_cases"]
            problem_fields = {
                key: value for key, value in problem_data.items() if key != "hidden_cases"
            }
            problem = Problem(exam_id=exam.id, **problem_fields)
            db.add(problem)
            db.flush()

            for sample in problem.samples:
                db.add(
                    Testcase(
                        problem_id=problem.id,
                        input_data=sample["input"],
                        expected_output=sample["output"],
                        is_hidden=0,
                    )
                )

            for hidden_case in hidden_cases:
                db.add(
                    Testcase(
                        problem_id=problem.id,
                        input_data=hidden_case["input"],
                        expected_output=hidden_case["output"],
                        is_hidden=1,
                    )
                )

    db.commit()
