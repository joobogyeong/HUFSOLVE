import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ClipboardList, FileText, Home, RefreshCw } from "lucide-react";
import { getExamAttempt, getReport } from "../api";
import { formatDateTime } from "../format";
import type { ExamHistory, LlmReport } from "../types";

const isReportGenerating = (status?: string | null) =>
  status === "PENDING" || status === "RUNNING";

const reportButtonLabel = (attempt: ExamHistory, report: LlmReport | null) => {
  const status = report?.status ?? attempt.reportStatus;
  if (!attempt.reportId) {
    return "리포트 없음";
  }
  if (isReportGenerating(status)) {
    return "리포트 생성중";
  }
  if (status === "SYSTEM_ERROR") {
    return "생성 실패";
  }
  return "리포트 보기";
};

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
        let reportStatus = next.reportStatus;
        if (next.reportId) {
          const nextReport = await getReport(next.reportId).catch(() => null);
          if (cancelled) return;
          setReport(nextReport);
          reportStatus = nextReport?.status ?? reportStatus;
        }
        if (next.status === "GRADING" || isReportGenerating(reportStatus)) {
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
            <div className="mt-6 flex flex-wrap gap-2">
              {attempt.status === "GRADING" && <div className="inline-flex items-center gap-2 font-black"><RefreshCw className="h-4 w-4 animate-spin" />최종 결과를 기다리는 중입니다.</div>}
              <button
                type="button"
                onClick={() => navigate(`/my/attempts/${attempt.attemptId}/report`)}
                disabled={!attempt.reportId}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-zinc-950 bg-white px-4 text-sm font-black text-zinc-950 transition hover:bg-zinc-950 hover:text-white disabled:cursor-not-allowed disabled:border-zinc-200 disabled:text-zinc-400 disabled:hover:bg-white"
              >
                <FileText className="h-4 w-4" />
                {reportButtonLabel(attempt, report)}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-zinc-200 bg-white p-5 text-center"><div className="text-sm font-bold text-zinc-500">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div>;
}
