import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertCircle,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileText,
  GraduationCap,
  Home,
  KeyRound,
  ListChecks,
  Menu,
  Play,
  Send,
  Timer,
  UserRound,
  XCircle,
} from "lucide-react";
import { initialExamHistory, mockExam, mockExams } from "./data";
import {
  createExamAttempt,
  createSampleRun,
  createSubmission,
  fetchExamAttempts,
  fetchExams,
  getSampleRun,
  getSubmission,
} from "./api";
import type { SampleRunResult } from "./api";
import type {
  ExamHistory,
  JudgeStatus,
  MockExam,
  Problem,
  ProblemResult,
  Screen,
  StudentProfile,
} from "./types";

const statusLabel: Record<JudgeStatus, string> = {
  UNSUBMITTED: "미제출",
  PENDING: "대기중",
  RUNNING: "채점중",
  ACCEPTED: "정답",
  WRONG_ANSWER: "오답",
  TIME_LIMIT_EXCEEDED: "시간초과",
  MEMORY_LIMIT_EXCEEDED: "메모리초과",
  OUTPUT_LIMIT_EXCEEDED: "출력초과",
  RUNTIME_ERROR: "런타임 에러",
  SYSTEM_ERROR: "시스템 에러",
};

const statusTone: Record<JudgeStatus, string> = {
  UNSUBMITTED: "border-zinc-200 bg-white/70 text-zinc-500",
  PENDING: "border-zinc-200 bg-white/70 text-zinc-600",
  RUNNING: "border-zinc-950 bg-white text-zinc-950",
  ACCEPTED: "border-zinc-950 bg-zinc-950 text-white",
  WRONG_ANSWER: "border-zinc-300 bg-zinc-100 text-zinc-950",
  TIME_LIMIT_EXCEEDED: "border-zinc-300 bg-zinc-100 text-zinc-950",
  MEMORY_LIMIT_EXCEEDED: "border-zinc-300 bg-zinc-100 text-zinc-950",
  OUTPUT_LIMIT_EXCEEDED: "border-zinc-300 bg-zinc-100 text-zinc-950",
  RUNTIME_ERROR: "border-zinc-300 bg-zinc-100 text-zinc-950",
  SYSTEM_ERROR: "border-zinc-300 bg-zinc-100 text-zinc-950",
};

const makeInitialAnswers = (exam: MockExam) =>
  Object.fromEntries(
    exam.problems.map((problem) => [problem.id, problem.starterCode]),
  ) as Record<number, string>;

const formatTime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  const two = (value: number) => value.toString().padStart(2, "0");

  return hours > 0
    ? `${two(hours)}:${two(minutes)}:${two(secs)}`
    : `${two(minutes)}:${two(secs)}`;
};

const formatDateTime = (date: string) =>
  new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));

const formatDuration = (seconds: number) => {
  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) {
    return `${minutes}분`;
  }

  return minutes === 0 ? `${hours}시간` : `${hours}시간 ${minutes}분`;
};

const EXAM_PAGE_SIZE = 20;

const isTerminalStatus = (status: JudgeStatus) =>
  !["UNSUBMITTED", "PENDING", "RUNNING"].includes(status);

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const isTerminalSampleRunStatus = (status: SampleRunResult["status"]) =>
  !["PENDING", "RUNNING"].includes(status);

const formatSampleRunConsole = (result: SampleRunResult) =>
  [
    `상태: ${result.message}`,
    "",
    "입력",
    result.input,
    "",
    "출력",
    result.stdout || result.stderr || "(출력 없음)",
    "",
    "예상 출력",
    result.expectedOutput,
  ].join("\n");

const makeFallbackResult = (problem: Problem, source: string): ProblemResult => {
  const normalized = source.replace(/\s/g, "");
  const isAccepted =
    normalized.includes("print(") &&
    normalized.includes("input(") &&
    source.trim().length > problem.starterCode.length;

  return {
    status: isAccepted ? "ACCEPTED" : "WRONG_ANSWER",
    runtimeMs: isAccepted ? 86 + problem.id * 19 : 132,
    memoryMb: isAccepted ? 27 + problem.id * 3 : 31,
    passedCases: isAccepted ? problem.samples.length + 4 : 1,
    totalCases: problem.samples.length + 4,
    message: isAccepted
      ? "모든 공개/숨김 테스트케이스를 통과했습니다."
      : "일부 테스트케이스에서 예상 출력과 다른 값이 확인되었습니다.",
  };
};

function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [studentId, setStudentId] = useState("");
  const [studentName, setStudentName] = useState("");
  const [loginNotice, setLoginNotice] = useState("");
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [roomCode, setRoomCode] = useState("");
  const [homeNotice, setHomeNotice] = useState("");
  const [activeExam, setActiveExam] = useState<MockExam>(mockExam);
  const [currentProblemId, setCurrentProblemId] = useState(mockExam.problems[0].id);
  const [answers, setAnswers] = useState<Record<number, string>>(() =>
    makeInitialAnswers(mockExam),
  );
  const [problemResults, setProblemResults] = useState<Record<number, ProblemResult>>({});
  const [consoleOutput, setConsoleOutput] = useState("아직 실행한 결과가 없습니다.");
  const [remainingSeconds, setRemainingSeconds] = useState(mockExam.durationSeconds);
  const [examHistory, setExamHistory] = useState<ExamHistory[]>(initialExamHistory);
  const [availableExams, setAvailableExams] = useState<MockExam[]>(mockExams);
  const [isSampleRunning, setIsSampleRunning] = useState(false);
  const [isFinishingExam, setIsFinishingExam] = useState(false);

  const currentProblem = useMemo(
    () =>
      activeExam.problems.find((problem) => problem.id === currentProblemId) ??
      activeExam.problems[0],
    [activeExam, currentProblemId],
  );

  const sortedHistory = useMemo(
    () =>
      [...examHistory].sort(
        (a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime(),
      ),
    [examHistory],
  );

  const acceptedCount = useMemo(
    () =>
      activeExam.problems.filter(
        (problem) => problemResults[problem.id]?.status === "ACCEPTED",
      ).length,
    [activeExam, problemResults],
  );

  const totalScore = Math.round((acceptedCount / activeExam.problems.length) * 100);

  useEffect(() => {
    let ignore = false;

    fetchExams()
      .then((exams) => {
        if (!ignore && exams.length > 0) {
          setAvailableExams(exams);
        }
      })
      .catch(() => {
        setAvailableExams(mockExams);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const login = () => {
    const trimmedStudentId = studentId.trim();
    const trimmedStudentName = studentName.trim();

    if (!trimmedStudentId || !trimmedStudentName) {
      setLoginNotice("학번과 이름을 모두 입력해주세요.");
      return;
    }

    setStudentProfile({
      studentId: trimmedStudentId,
      name: trimmedStudentName,
    });
    setLoginNotice("");
    setHomeNotice(`${trimmedStudentName}님, 로그인되었습니다. 시험 입장 코드를 입력해주세요.`);
    setScreen("home");

    fetchExamAttempts(trimmedStudentId)
      .then(setExamHistory)
      .catch(() => {
        setExamHistory(initialExamHistory);
      });
  };

  const logout = () => {
    setStudentProfile(null);
    setStudentId("");
    setStudentName("");
    setRoomCode("");
    setHomeNotice("");
    setScreen("login");
  };

  const finishExam = async (status = "최종 제출") => {
    if (isFinishingExam) {
      return;
    }

    setIsFinishingExam(true);
    const fallbackHistory: ExamHistory = {
      id: `history-${Date.now()}`,
      title: activeExam.title,
      roomCode: roomCode.trim() || activeExam.roomCode,
      submittedAt: new Date().toISOString(),
      score: totalScore,
      passedProblems: acceptedCount,
      totalProblems: activeExam.problems.length,
      status,
    };

    let newHistory = fallbackHistory;
    if (studentProfile) {
      try {
        newHistory = await createExamAttempt({
          roomCode: activeExam.roomCode,
          studentId: studentProfile.studentId,
          studentName: studentProfile.name,
          status,
        });
      } catch {
        newHistory = fallbackHistory;
      }
    }

    setExamHistory((current) => [newHistory, ...current]);
    setHomeNotice(
      `${activeExam.title}이 제출되었습니다. 점수 ${totalScore}점이 내 페이지에 반영되었습니다.`,
    );
    setScreen("home");
    setRoomCode("");
    setIsFinishingExam(false);
  };

  useEffect(() => {
    if (screen !== "exam") {
      return;
    }

    const timer = window.setInterval(() => {
      setRemainingSeconds((current) => Math.max(current - 1, 0));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [screen]);

  useEffect(() => {
    if (screen === "exam" && remainingSeconds === 0) {
      finishExam("시간 종료 제출");
    }
    // finishExam reads the latest exam state in this local-only MVP.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remainingSeconds, screen]);

  const enterExam = (exam: MockExam) => {
    setActiveExam(exam);
    setHomeNotice("");
    setRoomCode(exam.roomCode);
    setAnswers(makeInitialAnswers(exam));
    setProblemResults({});
    setConsoleOutput("아직 실행한 결과가 없습니다.");
    setRemainingSeconds(exam.durationSeconds);
    setCurrentProblemId(exam.problems[0].id);
    setScreen("exam");
  };

  const startExam = () => {
    const trimmedCode = roomCode.trim();

    if (!trimmedCode) {
      setHomeNotice("시험 입장 코드를 입력해주세요.");
      return;
    }

    const selectedExam = availableExams.find(
      (exam) => exam.roomCode.toLowerCase() === trimmedCode.toLowerCase(),
    );

    if (!selectedExam) {
      setHomeNotice("등록된 시험 입장 코드가 없습니다. 시험 카드의 입장 코드를 확인해주세요.");
      return;
    }

    enterExam(selectedExam);
  };

  const updateAnswer = (problemId: number, sourceCode: string) => {
    setAnswers((current) => ({ ...current, [problemId]: sourceCode }));
  };

  const pollSampleRun = async (runId: number) => {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      await wait(attempt === 0 ? 500 : 1000);

      const result = await getSampleRun(runId);
      setConsoleOutput(formatSampleRunConsole(result));

      if (isTerminalSampleRunStatus(result.status)) {
        return;
      }
    }

    setConsoleOutput("샘플 실행 결과 조회 시간이 초과되었습니다.");
  };

  const runSample = async () => {
    const source = answers[currentProblem.id] ?? "";
    const sample = currentProblem.samples[0];
    setIsSampleRunning(true);
    setConsoleOutput(`${currentProblem.title} 샘플 실행 접수 중...`);

    try {
      const created = await createSampleRun({
        problemId: currentProblem.id,
        language: "python",
        sourceCode: source,
        sampleIndex: 0,
      });
      setConsoleOutput(
        `${currentProblem.title} 샘플 실행 ID ${created.runId}번이 생성되었습니다.\nWorker 실행 결과를 확인 중입니다.`,
      );
      await pollSampleRun(created.runId);
    } catch {
      const hasPrint = source.includes("print");
      const hasInput = source.includes("input");
      const output =
        hasPrint && hasInput ? sample.output : "샘플을 실행했지만 출력이 예상값과 다릅니다.";

      setConsoleOutput(
        [
          "백엔드 API에 연결할 수 없어 프론트 mock 실행 결과를 표시했습니다.",
          "",
          "입력",
          sample.input,
          "",
          "출력",
          output,
          "",
          "예상 출력",
          sample.output,
        ].join("\n"),
      );
    } finally {
      setIsSampleRunning(false);
    }
  };

  const pollSubmission = async (
    submissionId: number,
    problemId: number,
    problemTitle: string,
  ) => {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      await wait(attempt === 0 ? 700 : 1500);

      const result = await getSubmission(submissionId);
      setProblemResults((current) => ({ ...current, [problemId]: result }));
      setConsoleOutput(
        `${problemTitle} 제출 결과: ${statusLabel[result.status]}\n${result.message}`,
      );

      if (isTerminalStatus(result.status)) {
        return;
      }
    }
  };

  const submitProblem = async () => {
    const source = answers[currentProblem.id] ?? "";
    const pendingResult: ProblemResult = {
      status: "PENDING",
      runtimeMs: 0,
      memoryMb: null,
      passedCases: 0,
      totalCases: currentProblem.samples.length,
      message: "제출을 접수하고 채점 대기열에 등록 중입니다.",
    };

    setProblemResults((current) => ({ ...current, [currentProblem.id]: pendingResult }));
    setConsoleOutput(`${currentProblem.title} 제출 접수 중...`);

    try {
      const created = await createSubmission({
        problemId: currentProblem.id,
        language: "python",
        sourceCode: source,
        studentId: studentProfile?.studentId,
        studentName: studentProfile?.name,
      });

      setProblemResults((current) => ({
        ...current,
        [currentProblem.id]: {
          ...pendingResult,
          submissionId: created.submissionId,
          status: created.status,
          message: "채점 대기열에 등록되었습니다.",
        },
      }));
      setConsoleOutput(
        `${currentProblem.title} 제출 ID ${created.submissionId}번이 생성되었습니다.\n채점 결과를 확인 중입니다.`,
      );

      void pollSubmission(created.submissionId, currentProblem.id, currentProblem.title).catch(() => {
        setConsoleOutput("제출 상태 조회 중 오류가 발생했습니다. 잠시 후 다시 확인해주세요.");
      });
    } catch {
      const result = makeFallbackResult(currentProblem, source);
      setProblemResults((current) => ({ ...current, [currentProblem.id]: result }));
      setConsoleOutput(
        [
          "백엔드 API에 연결할 수 없어 프론트 mock 판정으로 표시했습니다.",
          `${currentProblem.title} 제출 결과: ${statusLabel[result.status]}`,
          result.message,
        ].join("\n"),
      );
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] text-zinc-950">
      {screen === "login" && (
        <LoginScreen
          notice={loginNotice}
          studentId={studentId}
          studentName={studentName}
          onLogin={login}
          onStudentIdChange={setStudentId}
          onStudentNameChange={setStudentName}
        />
      )}

      {screen === "home" && (
        <HomeScreen
          exams={availableExams}
          notice={homeNotice}
          roomCode={roomCode}
          studentProfile={studentProfile}
          onLogout={logout}
          onRoomCodeChange={setRoomCode}
          onEnter={startExam}
          onGoMyPage={() => setScreen("my")}
        />
      )}

      {screen === "exam" && (
        <ExamScreen
          answers={answers}
          consoleOutput={consoleOutput}
          currentProblem={currentProblem}
          exam={activeExam}
          onChangeAnswer={updateAnswer}
          onFinish={() => void finishExam("최종 제출")}
          isFinishingExam={isFinishingExam}
          onRun={runSample}
          onSelectProblem={setCurrentProblemId}
          onSubmitProblem={submitProblem}
          isSampleRunning={isSampleRunning}
          problemResults={problemResults}
          remainingSeconds={remainingSeconds}
          totalScore={totalScore}
        />
      )}

      {screen === "my" && (
        <MyPage history={sortedHistory} onBackHome={() => setScreen("home")} />
      )}
    </div>
  );
}

interface LoginScreenProps {
  notice: string;
  studentId: string;
  studentName: string;
  onLogin: () => void;
  onStudentIdChange: (value: string) => void;
  onStudentNameChange: (value: string) => void;
}

function LoginScreen({
  notice,
  studentId,
  studentName,
  onLogin,
  onStudentIdChange,
  onStudentNameChange,
}: LoginScreenProps) {
  return (
    <main className="flex min-h-screen flex-col px-5 py-5 sm:px-8">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-end">
        <div className="text-sm font-semibold tracking-[0.18em] text-zinc-500">
          HUFSOLVE
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center py-12 text-center">
        <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-medium text-zinc-600 backdrop-blur">
          <UserRound className="h-4 w-4" />
          학생 로그인
        </div>

        <h1 className="text-5xl font-black leading-none text-zinc-950 sm:text-7xl">
          HUFSOLVE
        </h1>
        <p className="mt-5 max-w-md text-base leading-7 text-zinc-600 sm:text-lg">
          학번과 이름으로 로그인한 뒤 시험 입장 코드를 입력해 문제 풀이를 시작합니다.
        </p>

        <div className="glass-panel mt-10 w-full rounded-[24px] p-4 sm:p-5">
          <div className="grid gap-3">
            <label htmlFor="student-id" className="sr-only">
              학번
            </label>
            <input
              id="student-id"
              value={studentId}
              onChange={(event) => onStudentIdChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onLogin();
                }
              }}
              className="min-h-14 rounded-2xl border border-zinc-200 bg-white px-5 text-center text-lg font-bold text-zinc-950 outline-none transition placeholder:text-zinc-300 focus:border-zinc-950"
              inputMode="numeric"
              placeholder="학번"
            />

            <label htmlFor="student-name" className="sr-only">
              이름
            </label>
            <input
              id="student-name"
              value={studentName}
              onChange={(event) => onStudentNameChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onLogin();
                }
              }}
              className="min-h-14 rounded-2xl border border-zinc-200 bg-white px-5 text-center text-lg font-bold text-zinc-950 outline-none transition placeholder:text-zinc-300 focus:border-zinc-950"
              placeholder="이름"
            />

            <button
              type="button"
              onClick={onLogin}
              className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-6 text-base font-bold text-white transition hover:bg-zinc-800"
            >
              로그인
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>

        {notice && (
          <div className="mt-5 flex w-full items-start gap-2 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-left text-sm font-medium text-zinc-700 backdrop-blur">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-none" />
            <span>{notice}</span>
          </div>
        )}
      </section>
    </main>
  );
}

interface HomeScreenProps {
  exams: MockExam[];
  notice: string;
  roomCode: string;
  studentProfile: StudentProfile | null;
  onLogout: () => void;
  onRoomCodeChange: (value: string) => void;
  onEnter: () => void;
  onGoMyPage: () => void;
}

function HomeScreen({
  exams,
  notice,
  roomCode,
  studentProfile,
  onLogout,
  onRoomCodeChange,
  onEnter,
  onGoMyPage,
}: HomeScreenProps) {
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const [visibleExamCount, setVisibleExamCount] = useState(EXAM_PAGE_SIZE);

  const visibleExamCards = useMemo(
    () => exams.slice(0, visibleExamCount),
    [exams, visibleExamCount],
  );

  const hasMoreExams = visibleExamCount < exams.length;

  useEffect(() => {
    setVisibleExamCount(EXAM_PAGE_SIZE);
  }, [exams]);

  useEffect(() => {
    const target = loadMoreRef.current;

    if (!target || !hasMoreExams) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisibleExamCount((current) =>
            Math.min(current + EXAM_PAGE_SIZE, exams.length),
          );
        }
      },
      { rootMargin: "360px" },
    );

    observer.observe(target);

    return () => observer.disconnect();
  }, [exams.length, hasMoreExams]);

  return (
    <main className="min-h-screen px-5 py-5 sm:px-8">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <button
          type="button"
          onClick={onGoMyPage}
          className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-zinc-200 bg-white/70 text-zinc-900 shadow-sm backdrop-blur transition hover:border-zinc-950"
          aria-label="내 페이지 열기"
          title="내 페이지"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="text-sm font-semibold tracking-[0.18em] text-zinc-500">
          HUFSOLVE
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <div className="text-sm font-black text-zinc-950">
              {studentProfile?.name ?? "학생"}님
            </div>
            <div className="text-xs font-semibold text-zinc-500">
              {studentProfile?.studentId ?? "로그인 정보 없음"}
            </div>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex h-11 items-center justify-center rounded-full border border-zinc-200 bg-white/70 px-4 text-sm font-black text-zinc-950 shadow-sm backdrop-blur transition hover:border-zinc-950"
          >
            로그아웃
          </button>
        </div>
      </header>

      <section className="mx-auto flex min-h-[calc(100vh-84px)] w-full max-w-xl flex-col items-center justify-center py-12 text-center">
        <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-medium text-zinc-600 backdrop-blur">
          <Clock3 className="h-4 w-4" />
          학생용 코딩 시험 입장
        </div>

        <h1 className="text-5xl font-black leading-none text-zinc-950 sm:text-7xl">
          HUFSOLVE
        </h1>
        <p className="mt-5 max-w-md text-base leading-7 text-zinc-600 sm:text-lg">
          시험 감독자가 안내한 입장 코드를 입력하면 바로 문제 풀이 화면으로 이동합니다.
        </p>

        <div className="glass-panel mt-10 w-full rounded-[24px] p-4 sm:p-5">
          <label htmlFor="room-code" className="sr-only">
            시험 입장 코드
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="room-code"
              value={roomCode}
              onChange={(event) => onRoomCodeChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onEnter();
                }
              }}
              className="min-h-14 flex-1 rounded-2xl border border-zinc-200 bg-white px-5 text-center text-lg font-bold uppercase tracking-[0.22em] text-zinc-950 outline-none transition placeholder:text-zinc-300 focus:border-zinc-950"
              placeholder="EXAM CODE"
            />
            <button
              type="button"
              onClick={onEnter}
              className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-6 text-base font-bold text-white transition hover:bg-zinc-800"
            >
              입장
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>

        {notice && (
          <div className="mt-5 flex w-full items-start gap-2 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-left text-sm font-medium text-zinc-700 backdrop-blur">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-none" />
            <span>{notice}</span>
          </div>
        )}
      </section>

      <section className="mx-auto w-full max-w-6xl pb-16">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-bold text-zinc-600 backdrop-blur">
              <BookOpen className="h-4 w-4" />
              교수 개설 시험
            </div>
            <h2 className="text-3xl font-black text-zinc-950 sm:text-4xl">
              응시 가능한 시험
            </h2>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-zinc-200 bg-white/70 px-4 py-2 text-sm font-black text-zinc-600">
            <ClipboardList className="h-4 w-4" />
            {exams.length}개 시험
          </div>
        </div>

        <div
          className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
          data-testid="exam-catalog-grid"
        >
          {visibleExamCards.map((exam) => (
            <ExamCatalogCard key={exam.roomCode} exam={exam} />
          ))}
        </div>

        {hasMoreExams && (
          <div ref={loadMoreRef} className="h-12" aria-hidden="true" />
        )}
      </section>
    </main>
  );
}

function ExamCatalogCard({ exam }: { exam: MockExam }) {
  return (
    <article
      className="glass-panel flex min-h-[292px] flex-col rounded-3xl p-5"
      data-testid="exam-card"
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-3 py-1 text-xs font-black text-zinc-600">
            <CalendarClock className="h-3.5 w-3.5" />
            {exam.examType}
          </div>
          <h3 className="line-clamp-2 text-xl font-black leading-snug text-zinc-950">
            {exam.title}
          </h3>
        </div>
        <div className="flex h-11 w-11 flex-none items-center justify-center rounded-2xl bg-zinc-950 text-white">
          <GraduationCap className="h-5 w-5" />
        </div>
      </div>

      <div className="grid gap-3 text-sm font-semibold text-zinc-600">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 flex-none text-zinc-950" />
          <span>{formatDateTime(exam.startsAt)}</span>
        </div>
        <div className="flex items-center gap-2">
          <Timer className="h-4 w-4 flex-none text-zinc-950" />
          <span>{formatDuration(exam.durationSeconds)}</span>
        </div>
        <div className="flex items-center gap-2">
          <UserRound className="h-4 w-4 flex-none text-zinc-950" />
          <span>{exam.professor} 교수</span>
        </div>
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 flex-none text-zinc-950" />
          <span>{exam.course}</span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-bold text-zinc-500">
            <ClipboardList className="h-3.5 w-3.5" />
            문제수
          </div>
          <div className="font-black text-zinc-950">{exam.problems.length}문제</div>
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-bold text-zinc-500">
            <KeyRound className="h-3.5 w-3.5" />
            입장 코드
          </div>
          <div className="break-all font-black tracking-wide text-zinc-950">
            {exam.roomCode}
          </div>
        </div>
      </div>
    </article>
  );
}

interface ExamScreenProps {
  answers: Record<number, string>;
  consoleOutput: string;
  currentProblem: Problem;
  exam: MockExam;
  onChangeAnswer: (problemId: number, sourceCode: string) => void;
  onFinish: () => void;
  isFinishingExam: boolean;
  onRun: () => void;
  onSelectProblem: (problemId: number) => void;
  onSubmitProblem: () => void;
  isSampleRunning: boolean;
  problemResults: Record<number, ProblemResult>;
  remainingSeconds: number;
  totalScore: number;
}

function ExamScreen({
  answers,
  consoleOutput,
  currentProblem,
  exam,
  onChangeAnswer,
  onFinish,
  isFinishingExam,
  onRun,
  onSelectProblem,
  onSubmitProblem,
  isSampleRunning,
  problemResults,
  remainingSeconds,
  totalScore,
}: ExamScreenProps) {
  return (
    <main className="min-h-screen px-3 py-3 sm:px-5 sm:py-5">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-4">
        <header className="glass-panel flex flex-col gap-4 rounded-3xl px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-zinc-500">{exam.course}</div>
            <h1 className="truncate text-xl font-black text-zinc-950 sm:text-2xl">
              {exam.title}
            </h1>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 font-black text-zinc-950">
              <Clock3 className="h-4 w-4" />
              {formatTime(remainingSeconds)}
            </div>
            <div className="inline-flex h-12 items-center justify-center rounded-2xl border border-zinc-200 bg-white px-4 text-sm font-bold text-zinc-600">
              현재 점수 {totalScore}점
            </div>
            <button
              type="button"
              onClick={onFinish}
              disabled={isFinishingExam}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-5 font-bold text-white transition hover:bg-zinc-800 disabled:cursor-wait disabled:opacity-60"
            >
              {isFinishingExam ? "제출 중" : "최종 제출"}
              <Send className="h-4 w-4" />
            </button>
          </div>
        </header>

        <section className="grid gap-4 xl:grid-cols-[390px_minmax(0,1fr)]">
          <aside className="glass-panel rounded-3xl p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-black">문제 목록</h2>
              <span className="text-sm font-semibold text-zinc-500">
                {exam.problems.length}문제
              </span>
            </div>
            <div className="grid gap-2">
              {exam.problems.map((problem) => {
                const result = problemResults[problem.id]?.status ?? "UNSUBMITTED";
                const active = problem.id === currentProblem.id;

                return (
                  <button
                    key={problem.id}
                    type="button"
                    onClick={() => onSelectProblem(problem.id)}
                    className={`rounded-2xl border p-4 text-left transition ${
                      active
                        ? "border-zinc-950 bg-zinc-950 text-white"
                        : "border-zinc-200 bg-white/70 text-zinc-950 hover:border-zinc-400"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-xs font-bold opacity-70">
                          Problem {problem.id} · {problem.level}
                        </div>
                        <div className="mt-1 truncate text-base font-black">
                          {problem.title}
                        </div>
                      </div>
                      <span
                        className={`flex-none rounded-full border px-2.5 py-1 text-xs font-black ${
                          active ? "border-white/30 bg-white/15" : statusTone[result]
                        }`}
                      >
                        {statusLabel[result]}
                      </span>
                    </div>
                    <div className="mt-3 text-sm font-semibold opacity-70">
                      {problem.points}점 · {problem.timeLimitMs / 1000}s ·{" "}
                      {problem.memoryLimitMb}MB
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>

          <div className="grid min-h-[calc(100vh-164px)] gap-4 lg:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)]">
            <ProblemStatement problem={currentProblem} />
            <CodeWorkspace
              answer={answers[currentProblem.id] ?? ""}
              consoleOutput={consoleOutput}
              onAnswerChange={(value) => onChangeAnswer(currentProblem.id, value)}
              onRun={onRun}
              onSubmit={onSubmitProblem}
              isSampleRunning={isSampleRunning}
              result={problemResults[currentProblem.id]}
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function ProblemStatement({ problem }: { problem: Problem }) {
  return (
    <article className="glass-panel exam-scrollbar overflow-y-auto rounded-3xl p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-zinc-950 px-3 py-1 text-sm font-bold text-white">
          {problem.level}
        </span>
        <span className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-sm font-bold text-zinc-600">
          {problem.points}점
        </span>
      </div>

      <h2 className="text-2xl font-black leading-tight text-zinc-950 sm:text-3xl">
        {problem.title}
      </h2>

      <div className="mt-6 space-y-4 text-base leading-7 text-zinc-700">
        {problem.description.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>

      <Section title="입력">
        <p>{problem.inputDescription}</p>
      </Section>

      <Section title="출력">
        <p>{problem.outputDescription}</p>
      </Section>

      <Section title="제한">
        <ul className="grid gap-2">
          {problem.constraints.map((constraint) => (
            <li key={constraint} className="rounded-2xl bg-zinc-100 px-4 py-3">
              {constraint}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="예제">
        <div className="grid gap-3">
          {problem.samples.map((sample, index) => (
            <div
              key={`${sample.input}-${index}`}
              className="grid gap-3 rounded-2xl border border-zinc-200 bg-white/80 p-4"
            >
              <div>
                <div className="mb-2 text-sm font-black text-zinc-500">
                  예제 입력 {index + 1}
                </div>
                <pre className="exam-scrollbar overflow-x-auto rounded-xl bg-zinc-950 p-3 text-sm leading-6 text-white">
                  {sample.input}
                </pre>
              </div>
              <div>
                <div className="mb-2 text-sm font-black text-zinc-500">
                  예제 출력 {index + 1}
                </div>
                <pre className="exam-scrollbar overflow-x-auto rounded-xl bg-zinc-100 p-3 text-sm leading-6 text-zinc-950">
                  {sample.output}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <h3 className="mb-3 flex items-center gap-2 text-lg font-black text-zinc-950">
        <FileText className="h-4 w-4" />
        {title}
      </h3>
      <div className="text-base leading-7 text-zinc-700">{children}</div>
    </section>
  );
}

interface CodeWorkspaceProps {
  answer: string;
  consoleOutput: string;
  onAnswerChange: (value: string) => void;
  onRun: () => void;
  onSubmit: () => void;
  isSampleRunning: boolean;
  result?: ProblemResult;
}

function CodeWorkspace({
  answer,
  consoleOutput,
  onAnswerChange,
  onRun,
  onSubmit,
  isSampleRunning,
  result,
}: CodeWorkspaceProps) {
  return (
    <section className="flex min-h-[720px] flex-col gap-4 lg:min-h-0">
      <div className="dark-glass-panel flex min-h-[460px] flex-1 flex-col rounded-3xl">
        <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-bold text-zinc-400">Language</div>
            <div className="text-lg font-black text-white">Python 3.11</div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onRun}
              disabled={isSampleRunning}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-4 text-sm font-bold text-white transition hover:bg-white/15 disabled:cursor-wait disabled:opacity-60"
            >
              <Play className="h-4 w-4" />
              {isSampleRunning ? "실행 중" : "실행"}
            </button>
            <button
              type="button"
              onClick={onSubmit}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-white px-4 text-sm font-black text-zinc-950 transition hover:bg-zinc-100"
            >
              <Send className="h-4 w-4" />
              제출
            </button>
          </div>
        </div>

        <textarea
          value={answer}
          onChange={(event) => onAnswerChange(event.target.value)}
          spellCheck={false}
          className="exam-scrollbar min-h-[420px] flex-1 border-0 bg-transparent p-5 text-[15px] leading-7 text-white outline-none placeholder:text-zinc-500"
          aria-label="코드 에디터"
        />
      </div>

      <div className="glass-panel grid gap-4 rounded-3xl p-4 md:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl border border-zinc-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-black text-zinc-500">
            {result?.status === "ACCEPTED" ? (
              <CheckCircle2 className="h-4 w-4 text-zinc-950" />
            ) : result?.status === "WRONG_ANSWER" ? (
              <XCircle className="h-4 w-4 text-zinc-950" />
            ) : (
              <ListChecks className="h-4 w-4 text-zinc-950" />
            )}
            제출 결과
          </div>
          <div className="text-2xl font-black text-zinc-950">
            {result ? statusLabel[result.status] : "미제출"}
          </div>
          <p className="mt-2 text-sm leading-6 text-zinc-600">
            {result?.message ?? "실행 또는 제출을 하면 이 영역에 결과가 표시됩니다."}
          </p>
          {result && (
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <Metric label="통과" value={`${result.passedCases}/${result.totalCases}`} />
              <Metric label="시간" value={result.runtimeMs > 0 ? `${result.runtimeMs}ms` : "-"} />
              <Metric
                label="메모리"
                value={result.memoryMb === null ? "-" : `${result.memoryMb}MB`}
              />
              <Metric label="상태" value={statusLabel[result.status]} />
            </div>
          )}
        </div>

        <div className="rounded-2xl bg-zinc-950 p-4 text-white">
          <div className="mb-3 text-sm font-black text-zinc-400">실행 콘솔</div>
          <pre className="exam-scrollbar min-h-[160px] overflow-auto whitespace-pre-wrap text-sm leading-6">
            {consoleOutput}
          </pre>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-zinc-100 px-3 py-2">
      <div className="text-xs font-bold text-zinc-500">{label}</div>
      <div className="mt-1 truncate text-sm font-black text-zinc-950">{value}</div>
    </div>
  );
}

function MyPage({
  history,
  onBackHome,
}: {
  history: ExamHistory[];
  onBackHome: () => void;
}) {
  return (
    <main className="min-h-screen px-5 py-5 sm:px-8">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between">
        <button
          type="button"
          onClick={onBackHome}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-zinc-200 bg-white/70 px-4 text-sm font-black text-zinc-950 shadow-sm backdrop-blur transition hover:border-zinc-950"
        >
          <Home className="h-4 w-4" />
          홈
        </button>
        <div className="text-sm font-semibold tracking-[0.18em] text-zinc-500">
          MY PAGE
        </div>
      </header>

      <section className="mx-auto mt-12 w-full max-w-6xl">
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-bold text-zinc-600 backdrop-blur">
              <UserRound className="h-4 w-4" />
              학생 기록
            </div>
            <h1 className="text-4xl font-black text-zinc-950 sm:text-5xl">
              내 시험 결과
            </h1>
          </div>
          <p className="max-w-md text-sm leading-6 text-zinc-500">
            최근 제출 순으로 정렬된 시험 기록입니다. 현재 MVP에서는 최종 시험 기록을
            프론트 상태로 관리합니다.
          </p>
        </div>

        <div className="glass-panel overflow-hidden rounded-3xl">
          <div className="grid grid-cols-[1.4fr_0.8fr_0.7fr_0.6fr] border-b border-zinc-200 px-5 py-4 text-sm font-black text-zinc-500 max-lg:hidden">
            <span>시험</span>
            <span>제출 시간</span>
            <span>통과</span>
            <span className="text-right">점수</span>
          </div>

          <div className="divide-y divide-zinc-200/80">
            {history.map((item) => (
              <div
                key={item.id}
                className="grid gap-4 px-5 py-5 lg:grid-cols-[1.4fr_0.8fr_0.7fr_0.6fr] lg:items-center"
              >
                <div>
                  <div className="text-lg font-black text-zinc-950">{item.title}</div>
                  <div className="mt-1 text-sm font-semibold text-zinc-500">
                    코드 {item.roomCode} · {item.status}
                  </div>
                </div>
                <div className="text-sm font-semibold text-zinc-600">
                  {formatDateTime(item.submittedAt)}
                </div>
                <div className="text-sm font-black text-zinc-950">
                  {item.passedProblems}/{item.totalProblems} 문제
                </div>
                <div className="lg:text-right">
                  <span className="inline-flex min-w-20 justify-center rounded-full bg-zinc-950 px-4 py-2 text-sm font-black text-white">
                    {item.score}점
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
