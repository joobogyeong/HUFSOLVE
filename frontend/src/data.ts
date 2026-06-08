import type { ExamHistory, MockExam, Problem } from "./types";

const problemTitles = {
  computationalThinking: [
    "자기소개 출력하기",
    "짝수와 홀수 판별하기",
    "원의 넓이 구하기",
    "문자열 반복 출력",
    "점수 평균과 등급 계산하기",
    "장바구니 총 금액 계산하기",
    "리스트에서 짝수만 출력하기",
    "단어 길이 분류하기",
    "학생 성적 관리 프로그램",
    "간단한 도서 대출 관리",
  ],
  dataStructures: [
    "최근 주문 조회",
    "줄 서기 명단 관리",
    "단어 등장 횟수 세기",
    "괄호 문자열 검사",
    "중복 없는 대기 명단",
    "뒤로 가기",
    "프린터 대기열",
    "가장 가까운 큰 수",
    "우선순위 상담 시스템",
    "실시간 중앙값 관리",
  ],
  algorithms: [
    "최댓값과 최솟값 찾기",
    "숫자 카드 찾기",
    "합이 가장 큰 구간",
    "정렬된 두 배열 합치기",
    "회의실 배정",
    "예산 상한액 정하기",
    "미로 최단 거리",
    "섬의 개수 세기",
    "계단 오르기 최대 점수",
    "최소 비용 경로",
  ],
};

function mockProblems(startId: number, titles: string[]): Problem[] {
  return titles.map((title, index) => ({
    id: startId + index,
    title,
    level: index < 4 ? "Easy" : index < 8 ? "Medium" : "Hard",
    points: 10,
    timeLimitMs: index < 4 ? 2000 : index < 8 ? 3000 : 5000,
    memoryLimitMb: index < 4 ? 128 : 256,
    description: ["시험 문제를 불러오지 못해 기본 정보만 표시하고 있습니다."],
    inputDescription: "운영 API 연결 후 문제 입력 설명이 표시됩니다.",
    outputDescription: "운영 API 연결 후 문제 출력 설명이 표시됩니다.",
    constraints: [],
    samples: [],
    starterCode: `# ${title}\n# 여기에 코드를 작성하세요.\n`,
  }));
}

export const mockExams: MockExam[] = [
  {
    roomCode: "CT-MID",
    title: "컴퓨팅 사고 중간고사",
    course: "컴퓨팅 사고",
    professor: "신찬수",
    examType: "중간고사",
    durationSeconds: 60 * 120,
    startsAt: "2026-06-15T09:00:00+09:00",
    problems: mockProblems(1, problemTitles.computationalThinking),
  },
  {
    roomCode: "DS-MID",
    title: "자료구조 중간고사",
    course: "자료구조",
    professor: "신찬수",
    examType: "중간고사",
    durationSeconds: 60 * 120,
    startsAt: "2026-06-17T09:00:00+09:00",
    problems: mockProblems(11, problemTitles.dataStructures),
  },
  {
    roomCode: "ALG-MID",
    title: "알고리즘 중간고사",
    course: "알고리즘",
    professor: "신찬수",
    examType: "중간고사",
    durationSeconds: 60 * 120,
    startsAt: "2026-06-19T09:00:00+09:00",
    problems: mockProblems(21, problemTitles.algorithms),
  },
];

export const mockExam = mockExams[0];
export const initialExamHistory: ExamHistory[] = [];
