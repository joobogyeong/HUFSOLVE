import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ClipboardList, FileText, Home, RefreshCw } from "lucide-react";
import { getExamAttempt, getReport } from "../api";
import { formatDateTime } from "../format";
import type { ExamHistory, LlmReport, LlmReportStatus } from "../types";

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
                onClick={() => document.getElementById("ai-report")?.scrollIntoView({ behavior: "smooth" })}
                disabled={!attempt.reportId}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-zinc-950 bg-white px-4 text-sm font-black text-zinc-950 transition hover:bg-zinc-950 hover:text-white disabled:cursor-not-allowed disabled:border-zinc-200 disabled:text-zinc-400 disabled:hover:bg-white"
              >
                <FileText className="h-4 w-4" />
                {reportButtonLabel(attempt, report)}
              </button>
            </div>
            <ReportSection attempt={attempt} report={report} />
          </>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-zinc-200 bg-white p-5 text-center"><div className="text-sm font-bold text-zinc-500">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div>;
}

function ReportSection({
  attempt,
  report,
}: {
  attempt: ExamHistory;
  report: LlmReport | null;
}) {
  const status = report?.status ?? attempt.reportStatus;
  const isWaiting = isReportGenerating(status);
  const isCompleted = report?.status === "COMPLETED";
  const isError = status === "SYSTEM_ERROR";

  return (
    <section id="ai-report" className="mt-8 space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-bold text-zinc-600 backdrop-blur">
            <FileText className="h-4 w-4" />
            AI 학습 리포트
          </div>
          <h2 className="text-2xl font-black">제출 코드 리뷰</h2>
        </div>
        <div className="rounded-2xl border border-zinc-200 bg-white/70 px-4 py-3 text-center">
          <div className="text-xs font-bold text-zinc-500">리포트 상태</div>
          <div className="mt-1 text-sm font-black">{formatReportStatus(status)}</div>
        </div>
      </div>

      {!attempt.reportId && (
        <ReportStatusPanel title="아직 연결된 AI 리포트가 없습니다." message="문제 코드를 제출한 뒤 최종 제출하면 리포트가 생성됩니다." />
      )}
      {isWaiting && <ReportStatusPanel title="AI 리포트를 작성 중입니다." />}
      {isError && <ReportStatusPanel title="AI 리포트 생성에 실패했습니다." message={report?.errorMessage ?? "채점 결과는 저장되었지만 리포트 생성 중 문제가 발생했습니다."} />}

      {isCompleted && report && (
        <div className="space-y-5">
          <section className="glass-panel rounded-3xl p-6">
            <h3 className="text-xl font-black">전체 요약</h3>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-zinc-700">{report.summary}</p>
          </section>

          <section className="grid gap-5 lg:grid-cols-2">
            <ReportListCard title="잘한 점" items={report.strengths} />
            <ReportListCard title="보완할 점" items={report.weaknesses} />
          </section>

          <section className="glass-panel rounded-3xl p-6">
            <h3 className="text-xl font-black">문제별 코드 리뷰</h3>
            <div className="mt-5 space-y-4">
              {report.problemReviews.length === 0 ? (
                <p className="text-sm font-semibold text-zinc-500">아직 문제별 리뷰가 없습니다.</p>
              ) : (
                report.problemReviews.map((review) => (
                  <article key={`${review.problemId}-${review.title}`} className="rounded-2xl border border-zinc-200 bg-white/70 p-5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <h4 className="text-lg font-black">문제 {review.problemId}. {review.title}</h4>
                      <span className="inline-flex w-fit rounded-full bg-zinc-950 px-3 py-1 text-xs font-black text-white">{review.status} · {review.score}점</span>
                    </div>
                    <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-zinc-700">{review.feedback}</p>
                    {review.missingConcepts.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {review.missingConcepts.map((concept) => (
                          <span key={concept} className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-black text-zinc-600">{concept}</span>
                        ))}
                      </div>
                    )}
                    {review.nextStep && <p className="mt-4 text-sm font-bold leading-6 text-zinc-600">다음 단계: {review.nextStep}</p>}
                  </article>
                ))
              )}
            </div>
          </section>

          <ReportListCard title="다음 학습 계획" items={report.improvementPlan} />
        </div>
      )}
    </section>
  );
}

function formatReportStatus(status?: string | null) {
  const labels: Record<LlmReportStatus, string> = {
    PENDING: "생성 대기",
    RUNNING: "생성 중",
    COMPLETED: "생성 완료",
    SYSTEM_ERROR: "생성 실패",
  };
  return status && status in labels ? labels[status as LlmReportStatus] : "조회중";
}

function ReportStatusPanel({ title, message }: { title: string; message?: string }) {
  return (
    <div className="glass-panel rounded-3xl p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-zinc-950 text-white">
        <RefreshCw className={`h-5 w-5 ${message ? "" : "animate-spin"}`} />
      </div>
      <h3 className="mt-4 text-xl font-black">{title}</h3>
      {message && <p className="mt-3 text-sm font-semibold leading-6 text-zinc-500">{message}</p>}
    </div>
  );
}

function ReportListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="glass-panel rounded-3xl p-6">
      <h3 className="text-xl font-black">{title}</h3>
      <ul className="mt-4 space-y-3">
        {items.length === 0 ? (
          <li className="text-sm font-semibold text-zinc-500">아직 표시할 항목이 없습니다.</li>
        ) : (
          items.map((item) => (
            <li key={item} className="rounded-2xl bg-white/70 px-4 py-3 text-sm font-semibold leading-6 text-zinc-700">{item}</li>
          ))
        )}
      </ul>
    </section>
  );
}
