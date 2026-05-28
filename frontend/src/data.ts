import type { ExamHistory, MockExam } from "./types";

export const mockExam: MockExam = {
  roomCode: "HUF-2026",
  title: "클라우드 컴퓨팅 실습 평가",
  course: "Cloud Computing",
  durationSeconds: 60 * 75,
  startsAt: "2026-05-29T09:00:00+09:00",
  problems: [
    {
      id: 1,
      title: "A+B 자동 채점",
      level: "Easy",
      points: 30,
      timeLimitMs: 2000,
      memoryLimitMb: 128,
      description: [
        "두 정수 A와 B를 입력받아 합을 출력하세요.",
        "표준 입력으로 주어진 값을 읽고, 정답은 표준 출력으로만 출력해야 합니다.",
      ],
      inputDescription: "첫째 줄에 정수 A와 B가 공백으로 구분되어 주어집니다.",
      outputDescription: "A+B의 값을 한 줄에 출력합니다.",
      constraints: ["-1,000 <= A, B <= 1,000", "불필요한 문장은 출력하지 않습니다."],
      samples: [
        {
          input: "1 2",
          output: "3",
        },
        {
          input: "-4 9",
          output: "5",
        },
      ],
      starterCode:
        "a, b = map(int, input().split())\n# TODO: 두 수의 합을 출력하세요.\n",
    },
    {
      id: 2,
      title: "최댓값 찾기",
      level: "Medium",
      points: 35,
      timeLimitMs: 2000,
      memoryLimitMb: 128,
      description: [
        "정수 배열이 주어졌을 때 가장 큰 값을 출력하세요.",
        "배열의 길이는 첫 줄에 주어지고, 둘째 줄에 배열 원소가 주어집니다.",
      ],
      inputDescription: "첫째 줄에 N, 둘째 줄에 N개의 정수가 주어집니다.",
      outputDescription: "배열에서 가장 큰 정수를 출력합니다.",
      constraints: ["1 <= N <= 100,000", "-10^9 <= 각 원소 <= 10^9"],
      samples: [
        {
          input: "5\n3 1 9 2 7",
          output: "9",
        },
      ],
      starterCode:
        "n = int(input())\narr = list(map(int, input().split()))\n# TODO: 최댓값을 출력하세요.\n",
    },
    {
      id: 3,
      title: "요청 로그 집계",
      level: "Medium",
      points: 35,
      timeLimitMs: 3000,
      memoryLimitMb: 256,
      description: [
        "API 서버 로그에서 성공 응답의 개수를 집계하세요.",
        "각 로그는 HTTP status code 하나로 표현되며, 200 이상 300 미만이면 성공입니다.",
      ],
      inputDescription: "첫째 줄에 로그 수 N, 다음 N줄에 status code가 주어집니다.",
      outputDescription: "성공 응답의 개수를 출력합니다.",
      constraints: ["1 <= N <= 200,000", "100 <= status code <= 599"],
      samples: [
        {
          input: "6\n200\n201\n404\n500\n204\n302",
          output: "3",
        },
      ],
      starterCode:
        "n = int(input())\ncount = 0\nfor _ in range(n):\n    status = int(input())\n    # TODO: 성공 응답을 세어보세요.\nprint(count)\n",
    },
  ],
};

export const initialExamHistory: ExamHistory[] = [
  {
    id: "history-3",
    title: "자료구조 보충 테스트",
    roomCode: "DS-2401",
    submittedAt: "2026-05-21T16:20:00+09:00",
    score: 92,
    passedProblems: 5,
    totalProblems: 5,
    status: "채점 완료",
  },
  {
    id: "history-2",
    title: "알고리즘 중간 실습",
    roomCode: "ALGO-18",
    submittedAt: "2026-05-09T11:42:00+09:00",
    score: 78,
    passedProblems: 3,
    totalProblems: 4,
    status: "채점 완료",
  },
  {
    id: "history-1",
    title: "Python 기초 진단",
    roomCode: "PY-101",
    submittedAt: "2026-04-29T14:10:00+09:00",
    score: 100,
    passedProblems: 3,
    totalProblems: 3,
    status: "채점 완료",
  },
];
