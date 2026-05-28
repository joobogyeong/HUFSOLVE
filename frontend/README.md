# HUFSOLVE Frontend

React, Vite, TypeScript, Tailwind CSS 기반 학생용 코딩 시험 MVP입니다.

## 구현 범위

- 홈 화면: 시험 입장 코드 입력
- 시험 화면: 문제 설명, 코드 작성, 샘플 실행, 문제별 제출, 제한 시간 표시
- 내 페이지: 지금까지 응시한 시험 결과 목록
- 교사용 문제 등록/관리 화면은 MVP 범위에서 제외
- 문제, 채점 결과, 시험 기록은 mock data와 프론트 상태로 처리

## 실행

```bash
npm install
npm run dev
npm run build
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
