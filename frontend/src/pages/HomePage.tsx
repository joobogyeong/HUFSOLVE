import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  BookOpen,
  Check,
  ClipboardCopy,
  Clock3,
  GraduationCap,
  ListChecks,
  Send,
} from "lucide-react";
import { useApp } from "../AppContext";
import { formatDuration } from "../format";

export function HomePage() {
  const {
    activeDraft,
    attempts,
    attemptsReady,
    exams,
    examsReady,
    logout,
    notice,
    profile,
    startExam,
  } = useApp();
  const navigate = useNavigate();
  const [roomCode, setRoomCode] = useState("");
  const [localNotice, setLocalNotice] = useState("");
  const [copiedCode, setCopiedCode] = useState("");
  const ready = attemptsReady && examsReady;

  const enter = (code = roomCode) => {
    try {
      const draft = startExam(code.trim());
      navigate(`/exam/${draft.roomCode}`);
    } catch (error) {
      setLocalNotice(error instanceof Error ? error.message : "시험에 입장할 수 없습니다.");
    }
  };

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setLocalNotice(`${code} 코드를 복사했습니다. 상단 입력창에 붙여넣어 입장하세요.`);
    } catch {
      setRoomCode(code);
      setLocalNotice(`${code} 코드를 입력창에 채웠습니다.`);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-5 py-5">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <button type="button" onClick={() => navigate("/my")} className="rounded-full border border-zinc-200 bg-white px-4 py-3 text-sm font-black">마이페이지</button>
        <strong>HUFSOLVE</strong>
        <button type="button" onClick={() => { logout(); navigate("/login"); }} className="rounded-full border border-zinc-200 bg-white px-4 py-3 text-sm font-black">로그아웃</button>
      </header>

      <section className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center text-center">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/70 px-4 py-2 text-sm font-bold"><Clock3 className="h-4 w-4" />{profile?.name}님</div>
        <h1 className="text-5xl font-black sm:text-7xl">HUFSOLVE</h1>
        <p className="mt-4 text-zinc-600">시험 입장 코드를 입력해 문제 풀이를 시작합니다.</p>
        {activeDraft && activeDraft.studentId === profile?.studentId && (
          <button type="button" disabled={!ready} onClick={() => enter(activeDraft.roomCode)} className="mt-6 w-full rounded-2xl border border-zinc-950 bg-white p-4 font-black disabled:opacity-50">
            진행 중인 {activeDraft.roomCode} 시험으로 복귀
          </button>
        )}
        <div className="glass-panel mt-6 flex w-full gap-3 rounded-3xl p-5">
          <input disabled={!ready} value={roomCode} onChange={(event) => setRoomCode(event.target.value)} onKeyDown={(event) => event.key === "Enter" && ready && enter()} className="min-h-14 flex-1 rounded-2xl border border-zinc-200 px-5 text-center font-black uppercase disabled:opacity-50" placeholder="EXAM CODE" />
          <button type="button" disabled={!ready} onClick={() => enter()} className="inline-flex items-center gap-2 rounded-2xl bg-zinc-950 px-6 font-black text-white disabled:opacity-50">입장 <Send className="h-4 w-4" /></button>
        </div>
        {(localNotice || notice) && <div className="mt-5 flex w-full gap-2 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-left text-sm font-bold"><AlertCircle className="h-4 w-4 shrink-0" />{localNotice || notice}</div>}
      </section>

      <section className="mx-auto max-w-6xl pb-16">
        <div className="mb-5 flex items-center justify-between"><h2 className="text-3xl font-black">응시 가능한 시험</h2><span className="font-bold">{exams.length}개 시험</span></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {exams.map((exam) => {
            const attempted = attempts.some((attempt) => attempt.roomCode === exam.roomCode);
            return (
              <article key={exam.roomCode} className="glass-panel rounded-3xl p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-sm font-bold text-zinc-500"><BookOpen className="h-4 w-4" />{exam.course}</div>
                  <span className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-black">{exam.examType}</span>
                </div>
                <h3 className="text-xl font-black">{exam.title}</h3>
                <div className="mt-5 grid grid-cols-2 gap-2 text-sm font-bold text-zinc-600">
                  <div className="flex items-center gap-2 rounded-2xl bg-white/70 p-3"><GraduationCap className="h-4 w-4" />{exam.professor} 교수님</div>
                  <div className="flex items-center gap-2 rounded-2xl bg-white/70 p-3"><ListChecks className="h-4 w-4" />{exam.problems.length}문제</div>
                  <div className="col-span-2 flex items-center gap-2 rounded-2xl bg-white/70 p-3"><Clock3 className="h-4 w-4" />총 {formatDuration(exam.durationSeconds)}</div>
                </div>
                <div className="mt-5 rounded-2xl border border-zinc-200 bg-white p-3">
                  <div className="mb-2 flex items-center justify-between text-xs font-black text-zinc-500"><span>시험 코드</span>{attempted && <span>응시 완료</span>}</div>
                  <button type="button" aria-label={`${exam.roomCode} 코드 복사`} onClick={() => void copyCode(exam.roomCode)} className="inline-flex w-full items-center justify-between rounded-xl bg-zinc-950 px-4 py-3 font-black tracking-[0.18em] text-white">
                    {exam.roomCode}
                    {copiedCode === exam.roomCode ? <Check className="h-4 w-4" /> : <ClipboardCopy className="h-4 w-4" />}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
