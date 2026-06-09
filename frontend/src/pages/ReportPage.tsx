import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ClipboardList, FileText, Home, RefreshCw } from "lucide-react";
import { getExamAttempt, getReport } from "../api";
import { formatDateTime } from "../format";
import type { ExamHistory, LlmReport, LlmReportStatus } from "../types";

const isReportGenerating = (status?: string | null) =>
  status === "PENDING" || status === "RUNNING";

export function ReportPage() {
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
        const nextAttempt = await getExamAttempt(Number(attemptId));
        if (cancelled) {
          return;
        }

        setAttempt(nextAttempt);

        if (!nextAttempt.reportId) {
          setNotice("이 시험 기록에는 아직 연결된 AI 리포트가 없습니다.");
          if (nextAttempt.status === "GRADING") {
            timer = window.setTimeout(load, 2500);
          }
          return;
        }

        const nextReport = await getReport(nextAttempt.reportId);
        if (cancelled) {
          return;
        }

        setReport(nextReport);
        setNotice("");

        if (isReportGenerating(nextReport.status)) {
          timer = window.setTimeout(load, 2500);
        }
      } catch {
        if (!cancelled) {
          setNotice("AI 리포트를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
        }
      }
    };

    setReport(null);
    setNotice("");
    void load();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [attemptId]);

  const status = report?.status ?? attempt?.reportStatus;
  const isWaiting = isReportGenerating(status);
  const isCompleted = report?.status === "COMPLETED";
  const isError = status === "SYSTEM_ERROR";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-5 py-5">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <div className="flex gap-2">
          <button type="button" onClick={() => navigate("/my")} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-3 font-black"><ClipboardList className="h-4 w-4" />내 결과</button>
          <button type="button" onClick={() => navigate("/")} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-4 py-3 font-black"><Home className="h-4 w-4" />홈</button>
        </div>
        <strong>AI REPORT</strong>
      </header>

      <section className="mx-auto mt-12 max-w-6xl">
        {!attempt && !notice && <ReportStatusPanel title="AI 리포트를 불러오는 중입니다." />}

        {attempt && (
          <>
            <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/65 px-4 py-2 text-sm font-bold text-zinc-600 backdrop-blur">
                  <FileText className="h-4 w-4" />
                  AI 학습 리포트
                </div>
                <h1 className="text-4xl font-black sm:text-5xl">{attempt.title}</h1>
                <p className="mt-3 font-bold text-zinc-500">
                  코드 {attempt.roomCode} · {formatDateTime(attempt.submittedAt)}
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <Metric label="점수" value={attempt.status === "GRADING" ? "-" : `${attempt.score}점`} />
                <Metric label="통과" value={attempt.status === "GRADING" ? "-" : `${attempt.passedProblems}/${attempt.totalProblems}`} />
                <Metric label="상태" value={formatReportStatus(status)} />
              </div>
            </div>

            {notice && <div className="mb-4 rounded-2xl border border-zinc-200 bg-white/75 px-5 py-4 text-sm font-bold text-zinc-600">{notice}</div>}
            {isWaiting && <ReportStatusPanel title="AI 리포트를 작성 중입니다." />}
            {isError && <ReportStatusPanel title="AI 리포트 생성에 실패했습니다." message={report?.errorMessage ?? "채점 결과는 저장되었지만 리포트 생성 중 문제가 발생했습니다."} />}

            {isCompleted && report && (
              <div className="space-y-5">
                <section className="glass-panel rounded-3xl p-6">
                  <h2 className="text-xl font-black">전체 요약</h2>
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-zinc-700">{report.summary}</p>
                </section>

                <section className="grid gap-5 lg:grid-cols-2">
                  <ReportListCard title="잘한 점" items={report.strengths} />
                  <ReportListCard title="보완할 점" items={report.weaknesses} />
                </section>

                <section className="glass-panel rounded-3xl p-6">
                  <h2 className="text-xl font-black">문제별 코드 리뷰</h2>
                  <div className="mt-5 space-y-4">
                    {report.problemReviews.length === 0 ? (
                      <p className="text-sm font-semibold text-zinc-500">아직 문제별 리뷰가 없습니다.</p>
                    ) : (
                      report.problemReviews.map((review) => (
                        <article key={`${review.problemId}-${review.title}`} className="rounded-2xl border border-zinc-200 bg-white/70 p-5">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <h3 className="text-lg font-black">문제 {review.problemId}. {review.title}</h3>
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
          </>
        )}
      </section>
    </main>
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

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-zinc-200 bg-white/70 px-4 py-3"><div className="text-xs font-bold text-zinc-500">{label}</div><div className="mt-1 text-lg font-black">{value}</div></div>;
}

function ReportStatusPanel({ title, message }: { title: string; message?: string }) {
  return (
    <div className="glass-panel rounded-3xl p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-zinc-950 text-white">
        <RefreshCw className={`h-5 w-5 ${message ? "" : "animate-spin"}`} />
      </div>
      <h2 className="mt-4 text-xl font-black">{title}</h2>
      {message && <p className="mt-3 text-sm font-semibold leading-6 text-zinc-500">{message}</p>}
    </div>
  );
}

function ReportListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="glass-panel rounded-3xl p-6">
      <h2 className="text-xl font-black">{title}</h2>
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
