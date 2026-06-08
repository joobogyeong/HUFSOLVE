import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ClipboardList, Home, RefreshCw } from "lucide-react";
import { getExamAttempt, getReport } from "../api";
import { formatDateTime } from "../format";
import type { ExamHistory, LlmReport } from "../types";

export function AttemptPage() {
  const { attemptId = "" } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<ExamHistory | null>(null);
  const [report, setReport] = useState<LlmReport | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const load = async () => {
      try {
        const next = await getExamAttempt(Number(attemptId));
        if (cancelled) return;
        setAttempt(next);
        setNotice("");
        if (next.reportId) {
          getReport(next.reportId).then((value) => !cancelled && setReport(value)).catch(() => undefined);
        }
        if (next.status === "GRADING") {
          timer = window.setTimeout(load, 2500);
        }
      } catch {
        if (!cancelled) setNotice("시험 결과를 불러오지 못했습니다.");
      }
    };
    void load();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [attemptId]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-5 py-5">
      <header className="mx-auto flex max-w-6xl gap-2">
        <button type="button" onClick={() => navigate("/my")} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-3 font-black"><ClipboardList className="h-4 w-4" />내 결과</button>
        <button type="button" onClick={() => navigate("/")} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-3 font-black"><Home className="h-4 w-4" />홈</button>
      </header>
      <section className="mx-auto mt-12 max-w-5xl">
        {notice && <div className="rounded-2xl border border-zinc-200 bg-white p-5 font-bold">{notice}</div>}
        {!attempt && !notice && <div className="inline-flex items-center gap-2 font-black"><RefreshCw className="h-4 w-4 animate-spin" />결과 조회 중</div>}
        {attempt && (
          <>
            <h1 className="text-4xl font-black sm:text-5xl">{attempt.title}</h1>
            <p className="mt-3 font-bold text-zinc-500">{formatDateTime(attempt.submittedAt)} · {attempt.roomCode}</p>
            <div className="glass-panel mt-8 grid gap-4 rounded-3xl p-6 sm:grid-cols-3">
              <Metric label="상태" value={attempt.status === "GRADING" ? "채점 중" : attempt.status} />
              <Metric label="통과" value={attempt.status === "GRADING" ? "-" : `${attempt.passedProblems}/${attempt.totalProblems}`} />
              <Metric label="점수" value={attempt.status === "GRADING" ? "-" : `${attempt.score}점`} />
            </div>
            {attempt.status === "GRADING" && <div className="mt-6 inline-flex items-center gap-2 font-black"><RefreshCw className="h-4 w-4 animate-spin" />최종 결과를 기다리는 중입니다.</div>}
            {report?.status === "COMPLETED" && <article className="glass-panel mt-6 rounded-3xl p-6"><h2 className="text-xl font-black">AI 학습 리포트</h2><p className="mt-4 whitespace-pre-wrap leading-7 text-zinc-700">{report.summary}</p></article>}
          </>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-zinc-200 bg-white p-5 text-center"><div className="text-sm font-bold text-zinc-500">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div>;
}
