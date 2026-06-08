import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider } from "react-router-dom";
import { AppProvider } from "./AppContext";
import { createAppRouter } from "./App";
import { mockExams } from "./data";
import { EXAM_DRAFT_STORAGE_KEY, PROFILE_STORAGE_KEY } from "./storage";
import type { ActiveExamDraft, ExamHistory } from "./types";
import * as api from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchExams: vi.fn(),
    fetchExamAttempts: vi.fn(),
    createExamAttempt: vi.fn(),
    getExamAttempt: vi.fn(),
    getReport: vi.fn(),
  };
});

const profile = { studentId: "20260001", name: "테스트 학생" };
const gradingAttempt: ExamHistory = {
  id: "history-1",
  attemptId: 1,
  title: mockExams[0].title,
  roomCode: mockExams[0].roomCode,
  submittedAt: new Date().toISOString(),
  score: 0,
  passedProblems: 0,
  totalProblems: mockExams[0].problems.length,
  status: "GRADING",
};

function makeDraft(overrides: Partial<ActiveExamDraft> = {}): ActiveExamDraft {
  const exam = mockExams[0];
  return {
    studentId: profile.studentId,
    studentName: profile.name,
    roomCode: exam.roomCode,
    startedAt: Date.now(),
    endsAt: Date.now() + 60_000,
    currentProblemId: exam.problems[0].id,
    answers: Object.fromEntries(exam.problems.map((problem) => [problem.id, problem.starterCode])),
    runInputs: Object.fromEntries(exam.problems.map((problem) => [problem.id, "test input"])),
    submissionState: "editing",
    locked: false,
    ...overrides,
  };
}

function renderAt(path: string) {
  window.history.pushState({}, "", path);
  const router = createAppRouter();
  const result = render(
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>,
  );
  return { ...result, router };
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.mocked(api.fetchExams).mockResolvedValue(mockExams);
  vi.mocked(api.fetchExamAttempts).mockResolvedValue([]);
  vi.mocked(api.createExamAttempt).mockResolvedValue(gradingAttempt);
  vi.mocked(api.getExamAttempt).mockResolvedValue(gradingAttempt);
  vi.stubGlobal("confirm", vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("routing and exam flow", () => {
  it("redirects protected routes to login", async () => {
    renderAt("/my");
    expect(await screen.findByText("학생 로그인")).toBeInTheDocument();
  });

  it("restores the session profile on refresh and logs out", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    renderAt("/");
    expect(await screen.findByText("테스트 학생님")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "로그아웃" }));
    expect(await screen.findByText("학생 로그인")).toBeInTheDocument();
    expect(sessionStorage.getItem(PROFILE_STORAGE_KEY)).toBeNull();
  });

  it("supports direct my-page access and grading polling", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    vi.mocked(api.fetchExamAttempts).mockResolvedValue([gradingAttempt]);
    renderAt("/my");
    expect(await screen.findByText("채점 중")).toBeInTheDocument();
    expect(api.fetchExamAttempts).toHaveBeenCalledWith(profile.studentId);
  });

  it("supports direct attempt-result access on refresh", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    vi.mocked(api.getExamAttempt).mockResolvedValue({
      ...gradingAttempt,
      status: "COMPLETED",
      score: 100,
      passedProblems: gradingAttempt.totalProblems,
    });
    renderAt("/my/attempts/1");
    expect(await screen.findByText(gradingAttempt.title)).toBeInTheDocument();
    expect(await screen.findByText("100점")).toBeInTheDocument();
  });

  it("recovers answers and the absolute end time from localStorage", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    const draft = makeDraft({
      answers: { ...makeDraft().answers, [mockExams[0].problems[0].id]: "print('restored')" },
    });
    localStorage.setItem(EXAM_DRAFT_STORAGE_KEY, JSON.stringify(draft));
    renderAt(`/exam/${draft.roomCode}`);
    expect(await screen.findByDisplayValue("print('restored')")).toBeInTheDocument();
    expect(screen.getByText(/0[01]:[0-9]{2}/)).toBeInTheDocument();
  });

  it("submits all answers once and returns home", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    const draft = makeDraft();
    localStorage.setItem(EXAM_DRAFT_STORAGE_KEY, JSON.stringify(draft));
    renderAt(`/exam/${draft.roomCode}`);
    await userEvent.click(await screen.findByRole("button", { name: /최종 제출/ }));
    await waitFor(() => expect(api.createExamAttempt).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.createExamAttempt).mock.calls[0][0].answers).toHaveLength(
      mockExams[0].problems.length,
    );
    expect(await screen.findByText(/마이페이지에서 채점 결과를 확인하세요/)).toBeInTheDocument();
    expect(localStorage.getItem(EXAM_DRAFT_STORAGE_KEY)).toBeNull();
  });

  it("blocks a second exam while another draft is active", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    localStorage.setItem(EXAM_DRAFT_STORAGE_KEY, JSON.stringify(makeDraft()));
    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: /DS-FIN 입장/ }));
    expect(await screen.findByText("이 브라우저에서는 한 번에 하나의 시험만 진행할 수 있습니다.")).toBeInTheDocument();
  });

  it("blocks re-entry after an attempt exists", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    vi.mocked(api.fetchExamAttempts).mockResolvedValue([
      { ...gradingAttempt, status: "COMPLETED", score: 100 },
    ]);
    renderAt("/");
    const button = await screen.findByRole("button", { name: "HUF-2026 응시 완료" });
    await waitFor(() => expect(button).toBeDisabled());
  });

  it("auto-submits an expired draft after session restoration", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    localStorage.setItem(
      EXAM_DRAFT_STORAGE_KEY,
      JSON.stringify(makeDraft({ endsAt: Date.now() - 1, locked: true })),
    );
    renderAt("/");
    await waitFor(() => expect(api.createExamAttempt).toHaveBeenCalledTimes(1));
    expect(localStorage.getItem(EXAM_DRAFT_STORAGE_KEY)).toBeNull();
  });

  it("keeps and locks an expired draft when automatic submission fails", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    localStorage.setItem(
      EXAM_DRAFT_STORAGE_KEY,
      JSON.stringify(makeDraft({ endsAt: Date.now() - 1 })),
    );
    vi.mocked(api.createExamAttempt).mockRejectedValue(new Error("offline"));
    renderAt("/");
    await waitFor(() => expect(api.createExamAttempt).toHaveBeenCalledTimes(1));
    const stored = JSON.parse(localStorage.getItem(EXAM_DRAFT_STORAGE_KEY) ?? "{}");
    expect(stored.submissionState).toBe("failed");
    expect(stored.locked).toBe(true);
  });

  it("cancels or confirms SPA navigation through the exam blocker", async () => {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    const draft = makeDraft();
    localStorage.setItem(EXAM_DRAFT_STORAGE_KEY, JSON.stringify(draft));
    vi.mocked(confirm).mockReturnValueOnce(false).mockReturnValueOnce(true);
    const { router } = renderAt(`/exam/${draft.roomCode}`);

    void router.navigate("/my");
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1));
    expect(screen.getByLabelText("코드 에디터")).toBeInTheDocument();
    expect(api.createExamAttempt).not.toHaveBeenCalled();

    void router.navigate("/my");
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(api.createExamAttempt).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/마이페이지에서 채점 결과를 확인하세요/)).toBeInTheDocument();
  });
});
