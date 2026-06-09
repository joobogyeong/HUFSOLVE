import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Home, RefreshCw } from "lucide-react";
import { useApp } from "../AppContext";
import { formatDateTime } from "../format";
import type { ExamHistory } from "../types";

const isReportGenerating = (status?: string | null) =>
  status === "PENDING" || status === "RUNNING";

const reportButtonLabel = (attempt: ExamHistory) => {
  if (!attempt.reportId) {
    return "리포트 없음";
  }
  if (isReportGenerating(attempt.reportStatus)) {
    return "리포트 생성중";
  }
  if (attempt.reportStatus === "SYSTEM_ERROR") {
    return "생성 실패";
  }
  return "리포트 보기";
};

export function MyPage() {
  const { attempts, refreshAttempts } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    if (
      !attempts.some(
        (attempt) => attempt.status === "GRADING" || isReportGenerating(attempt.reportStatus),
      )
    ) {
      return;
    }
    const timer = window.setTimeout(() => void refreshAttempts().catch(() => undefined), 2500);
    return () => window.clearTimeout(timer);
  }, [attempts, refreshAttempts]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-5 py-5">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <button type="button" onClick={() => navigate("/")} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-3 font-black"><Home className="h-4 w-4" />홈</button>
        <strong>MY PAGE</strong>
      </header>
      <section className="mx-auto mt-12 max-w-6xl">
        <h1 className="text-4xl font-black sm:text-5xl">내 시험 결과</h1>
        <div className="glass-panel mt-8 divide-y divide-zinc-200 overflow-hidden rounded-3xl">
          {attempts.length === 0 && <div className="p-6 font-bold text-zinc-500">아직 제출한 시험이 없습니다.</div>}
          {attempts.map((attempt) => (
            <div key={attempt.id} className="grid w-full gap-3 p-5 text-left sm:grid-cols-[1fr_auto_auto_auto] sm:items-center">
              <button type="button" onClick={() => navigate(`/my/attempts/${attempt.attemptId}`)} className="text-left">
                <div className="text-lg font-black">{attempt.title}</div>
                <div className="mt-1 text-sm font-bold text-zinc-500">{formatDateTime(attempt.submittedAt)} · {attempt.roomCode}</div>
              </button>
              <div className="font-black">{attempt.status === "GRADING" ? <span className="inline-flex items-center gap-2"><RefreshCw className="h-4 w-4 animate-spin" />채점 중</span> : `${attempt.passedProblems}/${attempt.totalProblems} 통과`}</div>
              <div className="rounded-full bg-zinc-950 px-4 py-2 text-center font-black text-white">{attempt.status === "GRADING" ? "-" : `${attempt.score}점`}</div>
              <button
                type="button"
                onClick={() => navigate(`/my/attempts/${attempt.attemptId}/report`)}
                disabled={!attempt.reportId}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-full border border-zinc-950 bg-white px-4 text-sm font-black text-zinc-950 transition hover:bg-zinc-950 hover:text-white disabled:cursor-not-allowed disabled:border-zinc-200 disabled:text-zinc-400 disabled:hover:bg-white"
              >
                <FileText className="h-4 w-4" />
                {reportButtonLabel(attempt)}
              </button>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
