import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { createExamAttempt, fetchExamAttempts, fetchExams } from "./api";
import { mockExams } from "./data";
import { readExamDraft, readProfile, writeExamDraft, writeProfile } from "./storage";
import type { ActiveExamDraft, ExamHistory, MockExam, StudentProfile } from "./types";

interface AppContextValue {
  profile: StudentProfile | null;
  exams: MockExam[];
  examsReady: boolean;
  attempts: ExamHistory[];
  attemptsReady: boolean;
  activeDraft: ActiveExamDraft | null;
  notice: string;
  login: (profile: StudentProfile) => void;
  logout: () => void;
  startExam: (roomCode: string) => ActiveExamDraft;
  saveDraft: (draft: ActiveExamDraft) => void;
  finalizeDraft: (draft: ActiveExamDraft) => Promise<ExamHistory>;
  refreshAttempts: () => Promise<ExamHistory[]>;
  clearNotice: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

const initialAnswers = (exam: MockExam) =>
  Object.fromEntries(exam.problems.map((problem) => [problem.id, problem.starterCode]));

const initialRunInputs = (exam: MockExam) =>
  Object.fromEntries(
    exam.problems.map((problem) => [problem.id, problem.samples[0]?.input ?? ""]),
  );

export function AppProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<StudentProfile | null>(() => readProfile());
  const [exams, setExams] = useState<MockExam[]>([]);
  const [examsReady, setExamsReady] = useState(false);
  const [attempts, setAttempts] = useState<ExamHistory[]>([]);
  const [attemptsReady, setAttemptsReady] = useState(false);
  const [activeDraft, setActiveDraft] = useState<ActiveExamDraft | null>(() => readExamDraft());
  const [notice, setNotice] = useState("");
  const finalizingRef = useRef<Promise<ExamHistory> | null>(null);
  const autoSubmitAttemptedRef = useRef("");
  const autoRetryTimerRef = useRef<number | null>(null);

  useEffect(() => {
    fetchExams()
      .then(setExams)
      .catch(() => setExams(mockExams))
      .finally(() => setExamsReady(true));
  }, []);

  const refreshAttempts = useCallback(async () => {
    if (!profile) {
      setAttempts([]);
      setAttemptsReady(false);
      return [];
    }
    try {
      const next = await fetchExamAttempts(profile.studentId);
      setAttempts(next);
      return next;
    } finally {
      setAttemptsReady(true);
    }
  }, [profile]);

  useEffect(() => {
    if (profile) {
      void refreshAttempts().catch(() => setNotice("시험 기록을 불러오지 못했습니다."));
    }
  }, [profile, refreshAttempts]);

  const login = useCallback((nextProfile: StudentProfile) => {
    writeProfile(nextProfile);
    setAttemptsReady(false);
    setProfile(nextProfile);
    setNotice("");
  }, []);

  const logout = useCallback(() => {
    writeProfile(null);
    setProfile(null);
    setAttempts([]);
    setAttemptsReady(false);
  }, []);

  const saveDraft = useCallback((draft: ActiveExamDraft) => {
    writeExamDraft(draft);
    setActiveDraft(draft);
  }, []);

  const startExam = useCallback(
    (roomCode: string) => {
      if (!profile) {
        throw new Error("로그인이 필요합니다.");
      }
      if (!examsReady || !attemptsReady) {
        throw new Error("시험과 응시 기록을 확인하는 중입니다.");
      }
      const exam = exams.find(
        (candidate) => candidate.roomCode.toLowerCase() === roomCode.toLowerCase(),
      );
      if (!exam) {
        throw new Error("등록된 시험 입장 코드가 없습니다.");
      }
      if (attempts.some((attempt) => attempt.roomCode === exam.roomCode)) {
        throw new Error("이미 최종 제출한 시험에는 다시 입장할 수 없습니다.");
      }
      const storedDraft = readExamDraft();
      if (storedDraft) {
        if (
          storedDraft.studentId === profile.studentId &&
          storedDraft.roomCode === exam.roomCode
        ) {
          setActiveDraft(storedDraft);
          return storedDraft;
        }
        throw new Error("이 브라우저에서는 한 번에 하나의 시험만 진행할 수 있습니다.");
      }

      const startedAt = Date.now();
      const draft: ActiveExamDraft = {
        studentId: profile.studentId,
        studentName: profile.name,
        roomCode: exam.roomCode,
        startedAt,
        endsAt: startedAt + exam.durationSeconds * 1000,
        currentProblemId: exam.problems[0].id,
        answers: initialAnswers(exam),
        runInputs: initialRunInputs(exam),
        submissionState: "editing",
        locked: false,
      };
      saveDraft(draft);
      return draft;
    },
    [attempts, attemptsReady, exams, examsReady, profile, saveDraft],
  );

  const finalizeDraft = useCallback(
    async (draft: ActiveExamDraft) => {
      if (finalizingRef.current) {
        return finalizingRef.current;
      }

      const submittingDraft = { ...draft, submissionState: "submitting" as const };
      saveDraft(submittingDraft);
      const request = createExamAttempt({
        roomCode: draft.roomCode,
        studentId: draft.studentId,
        studentName: draft.studentName,
        answers: Object.entries(draft.answers).map(([problemId, sourceCode]) => ({
          problemId: Number(problemId),
          language: "python",
          sourceCode,
        })),
      })
        .then(async (attempt) => {
          if (autoRetryTimerRef.current !== null) {
            window.clearTimeout(autoRetryTimerRef.current);
            autoRetryTimerRef.current = null;
          }
          writeExamDraft(null);
          setActiveDraft(null);
          setNotice("최종 제출이 접수되었습니다. 마이페이지에서 채점 결과를 확인하세요.");
          await refreshAttempts().catch(() => undefined);
          return attempt;
        })
        .catch((error) => {
          const failedDraft: ActiveExamDraft = {
            ...draft,
            submissionState: "failed",
            locked: draft.endsAt <= Date.now(),
          };
          saveDraft(failedDraft);
          throw error;
        })
        .finally(() => {
          finalizingRef.current = null;
        });

      finalizingRef.current = request;
      return request;
    },
    [refreshAttempts, saveDraft],
  );

  useEffect(() => {
    if (
      profile &&
      activeDraft &&
      activeDraft.studentId === profile.studentId &&
      activeDraft.endsAt <= Date.now() &&
      autoSubmitAttemptedRef.current !== `${profile.studentId}:${activeDraft.roomCode}`
    ) {
      autoSubmitAttemptedRef.current = `${profile.studentId}:${activeDraft.roomCode}`;
      void finalizeDraft({ ...activeDraft, locked: true }).catch(() => {
        setNotice("만료된 시험의 자동 제출에 실패했습니다. 다시 시도합니다.");
        autoRetryTimerRef.current = window.setTimeout(() => {
          autoRetryTimerRef.current = null;
          autoSubmitAttemptedRef.current = "";
          setActiveDraft(readExamDraft());
        }, 5000);
      });
    }
  }, [activeDraft, finalizeDraft, profile]);

  useEffect(
    () => () => {
      if (autoRetryTimerRef.current !== null) {
        window.clearTimeout(autoRetryTimerRef.current);
      }
    },
    [],
  );

  const value = useMemo<AppContextValue>(
    () => ({
      profile,
      exams,
      examsReady,
      attempts,
      attemptsReady,
      activeDraft,
      notice,
      login,
      logout,
      startExam,
      saveDraft,
      finalizeDraft,
      refreshAttempts,
      clearNotice: () => setNotice(""),
    }),
    [
      activeDraft,
      attempts,
      attemptsReady,
      exams,
      examsReady,
      finalizeDraft,
      login,
      logout,
      notice,
      profile,
      refreshAttempts,
      saveDraft,
      startExam,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const value = useContext(AppContext);
  if (!value) {
    throw new Error("useApp must be used inside AppProvider");
  }
  return value;
}
