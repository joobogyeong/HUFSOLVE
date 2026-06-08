import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker, useNavigate, useParams } from "react-router-dom";
import { AlertCircle, Clock3, FileText, Play, Send } from "lucide-react";
import { createSampleRun, getSampleRun } from "../api";
import { useApp } from "../AppContext";
import { formatTime } from "../format";
import type { ActiveExamDraft, Problem } from "../types";

const FINAL_CONFIRM =
  "모든 답안을 최종 제출하고 시험을 종료합니다. 이후에는 다시 입장할 수 없습니다. 제출하시겠습니까?";
const LEAVE_CONFIRM =
  "시험 페이지를 나가면 현재 답안이 최종 제출되고 시험이 종료됩니다. 이후에는 다시 입장할 수 없습니다. 나가시겠습니까?";

export function ExamPage() {
  const { roomCode = "" } = useParams();
  const {
    activeDraft,
    attemptsReady,
    exams,
    examsReady,
    finalizeDraft,
    profile,
    saveDraft,
    startExam,
  } = useApp();
  const navigate = useNavigate();
  const initialDraft =
    activeDraft?.roomCode === roomCode && activeDraft.studentId === profile?.studentId
      ? activeDraft
      : null;
  const [draft, setDraft] = useState<ActiveExamDraft | null>(initialDraft);
  const [now, setNow] = useState(Date.now());
  const [consoleOutput, setConsoleOutput] = useState("아직 실행한 결과가 없습니다.");
  const [notice, setNotice] = useState("");
  const [isSampleRunning, setIsSampleRunning] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);
  const allowNavigationRef = useRef(false);
  const draftRef = useRef(draft);

  const exam = useMemo(
    () => exams.find((candidate) => candidate.roomCode === roomCode),
    [exams, roomCode],
  );
  const currentProblem = exam?.problems.find(
    (problem) => problem.id === draft?.currentProblemId,
  ) ?? exam?.problems[0];

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  useEffect(() => {
    if (!profile || !roomCode || draft || !examsReady || !attemptsReady) {
      return;
    }
    try {
      setDraft(startExam(roomCode));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "시험에 입장할 수 없습니다.");
      navigate("/", { replace: true });
    }
  }, [attemptsReady, draft, examsReady, navigate, profile, roomCode, startExam]);

  useEffect(() => {
    if (!draft) {
      return;
    }
    const timer = window.setTimeout(() => saveDraft(draft), 400);
    const flush = () => saveDraft(draftRef.current ?? draft);
    window.addEventListener("pagehide", flush);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("pagehide", flush);
    };
  }, [draft, saveDraft]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const finish = useCallback(async () => {
    const current = draftRef.current;
    if (!current || isFinishing) {
      return;
    }
    setIsFinishing(true);
    try {
      await finalizeDraft(current);
      allowNavigationRef.current = true;
      navigate("/", { replace: true });
    } catch {
      setNotice("최종 제출에 실패했습니다. 답안을 유지한 채 다시 시도합니다.");
      setDraft((current) =>
        current
          ? {
              ...current,
              submissionState: "failed",
              locked: current.endsAt <= Date.now(),
            }
          : current,
      );
    } finally {
      setIsFinishing(false);
    }
  }, [finalizeDraft, isFinishing, navigate]);

  useEffect(() => {
    if (!draft || draft.endsAt > now || isFinishing) {
      return;
    }
    const locked = { ...draft, locked: true };
    setDraft(locked);
    saveDraft(locked);
    void finish();
  }, [draft, finish, isFinishing, now, saveDraft]);

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      Boolean(
        draft &&
          !allowNavigationRef.current &&
          currentLocation.pathname !== nextLocation.pathname,
      ),
  );

  useEffect(() => {
    if (blocker.state !== "blocked") {
      return;
    }
    if (!window.confirm(LEAVE_CONFIRM)) {
      blocker.reset();
      return;
    }
    const current = draftRef.current;
    if (!current) {
      blocker.proceed();
      return;
    }
    setIsFinishing(true);
    void finalizeDraft(current)
      .then(() => {
        allowNavigationRef.current = true;
        blocker.reset();
        navigate("/", { replace: true });
      })
      .catch(() => {
        setNotice("최종 제출에 실패해 시험 페이지에 남아 있습니다.");
        setDraft((current) =>
          current
            ? {
                ...current,
                submissionState: "failed",
                locked: current.endsAt <= Date.now(),
              }
            : current,
        );
        blocker.reset();
      })
      .finally(() => setIsFinishing(false));
  }, [blocker, finalizeDraft, navigate]);

  const updateDraft = (changes: Partial<ActiveExamDraft>) => {
    setDraft((current) => (current ? { ...current, ...changes } : current));
  };

  const runSample = async () => {
    if (!currentProblem || !draft) {
      return;
    }
    setIsSampleRunning(true);
    setConsoleOutput(`${currentProblem.title} 실행 접수 중...`);
    try {
      const created = await createSampleRun({
        problemId: currentProblem.id,
        language: "python",
        sourceCode: draft.answers[currentProblem.id] ?? "",
        inputData: draft.runInputs[currentProblem.id] ?? "",
      });
      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, attempt === 0 ? 500 : 1000));
        const result = await getSampleRun(created.runId);
        setConsoleOutput(
          [
            `상태: ${result.message}`,
            "",
            "출력",
            result.stdout || "(출력 없음)",
            result.stderr ? `\n오류\n${result.stderr}` : "",
          ].join("\n"),
        );
        if (!["PENDING", "RUNNING"].includes(result.status)) {
          break;
        }
      }
    } catch {
      setConsoleOutput("코드 실행 요청에 실패했습니다.");
    } finally {
      setIsSampleRunning(false);
    }
  };

  if (!exam || !draft || !currentProblem) {
    return <main className="p-8 font-bold">{notice || "시험을 불러오는 중입니다."}</main>;
  }

  const locked = draft.locked || draft.submissionState === "submitting";
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-3 py-3 sm:px-5 sm:py-5">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-4">
        <header className="glass-panel flex flex-col gap-4 rounded-3xl px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div><div className="text-sm font-semibold text-zinc-500">{exam.course}</div><h1 className="text-2xl font-black">{exam.title}</h1></div>
          <div className="flex gap-3">
            <div className="inline-flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 font-black"><Clock3 className="h-4 w-4" />{formatTime(draft.endsAt - now)}</div>
            <button type="button" disabled={isFinishing} onClick={() => window.confirm(FINAL_CONFIRM) && void finish()} className="inline-flex h-12 items-center gap-2 rounded-2xl bg-zinc-950 px-5 font-bold text-white disabled:opacity-50">{isFinishing ? "제출 중" : "최종 제출"}<Send className="h-4 w-4" /></button>
          </div>
        </header>
        {notice && <div className="flex gap-2 rounded-2xl border border-zinc-200 bg-white p-4 text-sm font-bold"><AlertCircle className="h-4 w-4" />{notice}</div>}
        {locked && <div className="rounded-2xl border border-zinc-300 bg-zinc-100 p-4 text-sm font-black">시험 시간이 종료되었거나 제출 중입니다. 답안 편집이 잠겼습니다.</div>}
        <section className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="glass-panel rounded-3xl p-4">
            <h2 className="mb-4 font-black">문제 목록</h2>
            <div className="grid gap-2">
              {exam.problems.map((problem) => (
                <button key={problem.id} type="button" onClick={() => updateDraft({ currentProblemId: problem.id })} className={`rounded-2xl border p-4 text-left font-black ${problem.id === currentProblem.id ? "border-zinc-950 bg-zinc-950 text-white" : "border-zinc-200 bg-white"}`}>
                  Problem {problem.id}<span className="mt-1 block truncate text-sm opacity-70">{problem.title}</span>
                </button>
              ))}
            </div>
          </aside>
          <div className="grid gap-4 lg:grid-cols-2">
            <ProblemPanel problem={currentProblem} />
            <section className="flex flex-col gap-4">
              <div className="dark-glass-panel flex min-h-[560px] flex-col rounded-3xl">
                <div className="flex items-center justify-between border-b border-white/10 p-4 text-white"><strong>Python 3.11</strong><button type="button" disabled={isSampleRunning || locked} onClick={() => void runSample()} className="inline-flex items-center gap-2 rounded-2xl border border-white/20 px-4 py-2 font-bold disabled:opacity-50"><Play className="h-4 w-4" />{isSampleRunning ? "실행 중" : "실행"}</button></div>
                <textarea aria-label="코드 에디터" disabled={locked} value={draft.answers[currentProblem.id] ?? ""} onChange={(event) => updateDraft({ answers: { ...draft.answers, [currentProblem.id]: event.target.value } })} className="min-h-[380px] flex-1 bg-transparent p-5 font-mono text-sm leading-7 text-white outline-none disabled:opacity-60" />
                <div className="border-t border-white/10 p-4"><label className="mb-2 block text-sm font-black text-white">실행 입력</label><textarea aria-label="실행 입력" disabled={locked} value={draft.runInputs[currentProblem.id] ?? ""} onChange={(event) => updateDraft({ runInputs: { ...draft.runInputs, [currentProblem.id]: event.target.value } })} className="min-h-24 w-full rounded-2xl border border-white/10 bg-black/20 p-3 text-white disabled:opacity-60" /></div>
              </div>
              <pre className="glass-panel min-h-40 whitespace-pre-wrap rounded-3xl bg-zinc-950 p-5 text-sm leading-6 text-white">{consoleOutput}</pre>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function ProblemPanel({ problem }: { problem: Problem }) {
  return (
    <article className="glass-panel rounded-3xl p-6">
      <div className="mb-3 text-sm font-black text-zinc-500">{problem.level} · {problem.points}점</div>
      <h2 className="text-3xl font-black">{problem.title}</h2>
      <div className="mt-6 space-y-3 leading-7 text-zinc-700">{problem.description.map((item) => <p key={item}>{item}</p>)}</div>
      <Section title="입력">{problem.inputDescription}</Section>
      <Section title="출력">{problem.outputDescription}</Section>
      <Section title="예제">{problem.samples.map((sample, index) => <pre key={index} className="mt-3 overflow-auto rounded-2xl bg-zinc-950 p-4 text-sm text-white">{sample.input}{"\n→ "}{sample.output}</pre>)}</Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mt-8"><h3 className="flex items-center gap-2 text-lg font-black"><FileText className="h-4 w-4" />{title}</h3><div className="mt-3 leading-7 text-zinc-700">{children}</div></section>;
}
