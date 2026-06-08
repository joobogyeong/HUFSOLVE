# HUFSOLVE Frontend

React, Vite, TypeScript, Tailwind CSS 기반 학생용 코딩 시험 MVP입니다.

## 구현 범위

- 홈 화면: 시험 입장 코드 입력
- 시험 화면: 문제 설명, 코드 작성, 샘플 실행, 답안 복구, 최종 일괄 제출
- 내 페이지: 채점 중 상태와 최종 시험 결과 목록
- 교사용 문제 등록/관리 화면은 MVP 범위에서 제외
- 로그인 프로필은 `sessionStorage`, 진행 중 시험 초안은 `localStorage`에 저장
- `/login`, `/`, `/exam/:roomCode`, `/my`, `/my/attempts/:attemptId` URL 라우팅

## 실행

```bash
npm install
npm run dev
npm run build
npm test
```

PowerShell 실행 정책 때문에 `npm` 실행이 막히는 환경에서는 `npm.cmd`를 사용합니다.

```bash
npm.cmd install
npm.cmd run dev
npm.cmd run build
```

## Vercel 배포

Vercel에서 프로젝트의 Root Directory를 `frontend`로 지정합니다.

- Framework: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
