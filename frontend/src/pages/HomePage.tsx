import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, BookOpen, ClipboardList, Clock3, Send } from "lucide-react";
import { useApp } from "../AppContext";
import { formatDateTime } from "../format";

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
  const ready = attemptsReady && examsReady;

  const enter = (code = roomCode) => {
    try {
      const draft = startExam(code.trim());
      navigate(`/exam/${draft.roomCode}`);
    } catch (error) {
      setLocalNotice(error instanceof Error ? error.message : "시험에 입장할 수 없습니다.");
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
                <div className="mb-3 flex items-center gap-2 text-sm font-bold text-zinc-500"><BookOpen className="h-4 w-4" />{exam.course}</div>
                <h3 className="text-xl font-black">{exam.title}</h3>
                <p className="mt-3 text-sm font-semibold text-zinc-600">{formatDateTime(exam.startsAt)} · {exam.problems.length}문제</p>
              <button type="button" aria-label={`${exam.roomCode} ${attempted ? "응시 완료" : "입장"}`} disabled={!ready || attempted} onClick={() => enter(exam.roomCode)} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-4 py-3 font-black text-white disabled:bg-zinc-300">
                  <ClipboardList className="h-4 w-4" />{attempted ? "응시 완료" : `${exam.roomCode} 입장`}
                </button>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
