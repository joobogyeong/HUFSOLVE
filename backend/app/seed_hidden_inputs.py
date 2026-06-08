from __future__ import annotations


HIDDEN_CASE_INPUTS: dict[str, list[str]] = {
    "자기소개 출력하기": [
        "Minji\n1\nHUFS",
        "Kim\n100\nKorea",
        "A\n42\nB",
    ],
    "짝수와 홀수 판별하기": ["2", "999999", "1000000"],
    "원의 넓이 구하기": ["1", "10", "100"],
    "문자열 반복 출력": ["x\n1", "ab\n4", "Z\n5"],
    "점수 평균과 등급 계산하기": [
        "79 80 81",
        "69 70 71",
        "0 0 0",
    ],
    "장바구니 총 금액 계산하기": [
        "1\npen 999 1",
        "2\napple 1000 10\nmilk 2500 2",
        "3\na 1000000 100\nb 1 1\nc 10 10",
    ],
    "리스트에서 짝수만 출력하기": [
        "1\n2",
        "5\n1 3 5 7 9",
        "6\n-2 -1 0 3 4 5",
    ],
    "단어 길이 분류하기": [
        "3\na\nabcd\nabcdefgh",
        "3\nabc\nabcdefg\nabcdefgh",
        "1\npython",
    ],
    "학생 성적 관리 프로그램": [
        "1\nA 100\n3\nfind A\naverage\nupdate A 0",
        "2\nA 0\nB 100\n4\naverage\nupdate A 100\naverage\nfind B",
        "3\nA 10\nB 20\nC 30\n5\nfind B\nupdate B 50\nfind B\naverage\nfind A",
    ],
    "간단한 도서 대출 관리": [
        "1\nPython\n3\ncheck Python\nborrow Python\ncheck Python",
        "2\nA B\n5\nborrow A\ncheck A\ncheck B\nreturn A\ncheck A",
        "3\nX Y Z\n7\nborrow X\nborrow Z\ncheck X\ncheck Y\nreturn X\ncheck X\ncheck Z",
    ],
    "최근 주문 조회": [
        "3\norder 1\nrecent\nrecent",
        "4\norder 7\norder 9\nrecent\nrecent",
        "5\norder 1000000\nrecent\norder 2\nrecent\nrecent",
    ],
    "줄 서기 명단 관리": [
        "5\npush A\nsize\npop\npush B\nsize",
        "6\npush A\npush B\npop\nsize\npop\nsize",
        "4\npush Solo\npop\npush Next\npop",
    ],
    "단어 등장 횟수 세기": [
        "1\na\n3\na b c",
        "6\na b a c b a\n4\na b c d",
        "5\nx x x x x\n2\nx y",
    ],
    "괄호 문자열 검사": ["()", "(()", ")("],
    "중복 없는 대기 명단": [
        "1\nMina",
        "5\nA\nA\nA\nB\nA",
        "6\nZ\nY\nZ\nX\nY\nW",
    ],
    "뒤로 가기": [
        "5\ncurrent\nvisit a\ncurrent\nback\ncurrent",
        "6\nvisit a\nvisit b\ncurrent\nback\ncurrent\ncurrent",
        "5\nback\ncurrent\nvisit x\nback\ncurrent",
    ],
    "프린터 대기열": [
        "1 0\n5",
        "4 2\n1 2 3 4",
        "6 5\n1 1 9 1 1 1",
    ],
    "가장 가까운 큰 수": [
        "1\n5",
        "5\n5 4 3 2 1",
        "5\n1 3 2 5 4",
    ],
    "우선순위 상담 시스템": [
        "3\nrequest A 2\nrequest B 1\nprocess",
        "5\nrequest A 1\nrequest B 1\nprocess\nprocess\nrequest C 1",
        "6\nrequest A 3\nrequest B 2\nrequest C 1\nprocess\nprocess\nprocess",
    ],
    "실시간 중앙값 관리": [
        "1\n10",
        "4\n5\n1\n3\n2",
        "5\n-1\n-2\n-3\n-4\n-5",
    ],
    "최댓값과 최솟값 찾기": [
        "1\n7",
        "4\n-5 -2 -9 -3",
        "5\n4 4 4 4 4",
    ],
    "숫자 카드 찾기": [
        "1\n5\n3\n5 4 6",
        "5\n-10 -5 0 5 10\n5\n-10 10 1 -5 0",
        "4\n1 2 3 4\n4\n4 3 2 1",
    ],
    "합이 가장 큰 구간": [
        "4 1\n-3 7 2 5",
        "4 4\n1 2 3 4",
        "5 2\n-5 -2 -3 -1 -4",
    ],
    "정렬된 두 배열 합치기": [
        "1 1\n1\n2",
        "3 2\n1 2 3\n10 20",
        "4 4\n1 2 2 5\n2 2 3 4",
    ],
    "회의실 배정": [
        "1\n0 1",
        "4\n0 1\n1 2\n2 3\n3 4",
        "4\n0 10\n1 2\n2 3\n3 4",
    ],
    "예산 상한액 정하기": [
        "3\n10 20 30\n100",
        "1\n100\n50",
        "5\n5 5 5 5 5\n17",
    ],
    "미로 최단 거리": [
        "2 2\n11\n11",
        "3 3\n111\n001\n111",
        "4 4\n1000\n1110\n0010\n0011",
    ],
    "섬의 개수 세기": [
        "1 1\n0",
        "1 1\n1",
        "3 3\n101\n010\n101",
    ],
    "계단 오르기 최대 점수": [
        "1\n7",
        "2\n10\n20",
        "5\n10\n20\n30\n40\n50",
    ],
    "최소 비용 경로": [
        "2\n1\n1 2 7\n1 2",
        "3\n3\n1 2 5\n1 2 2\n2 3 3\n1 3",
        "4\n5\n1 2 10\n1 3 1\n3 2 1\n2 4 1\n3 4 10\n1 4",
    ],
}
