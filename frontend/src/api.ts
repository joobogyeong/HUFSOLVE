import type { ExamHistory, JudgeStatus, LlmReport, MockExam, ProblemResult } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
const WAKE_API_URL = (import.meta.env.VITE_WAKE_API_URL ?? "").replace(/\/$/, "");
const WAKE_REUSE_MS = 5 * 60 * 1000;
const STARTUP_RETRY_ATTEMPTS = 24;

let lastWakeAt = 0;
let wakePromise: Promise<void> | null = null;

interface CreateSubmissionRequest {
  problemId: number;
  language: "python";
  sourceCode: string;
  studentId?: string;
  studentName?: string;
}

interface CreateSubmissionResponse {
  submissionId: number;
  status: JudgeStatus;
}

interface SubmissionResponse {
  submissionId: number;
  problemId: number;
  status: JudgeStatus;
  score: number;
  passedCases: number;
  totalCases: number;
  runtimeMs: number | null;
  memoryMb: number | null;
  message: string;
  errorMessage: string | null;
}

export type SampleRunStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "TIME_LIMIT_EXCEEDED"
  | "MEMORY_LIMIT_EXCEEDED"
  | "OUTPUT_LIMIT_EXCEEDED"
  | "RUNTIME_ERROR"
  | "SYSTEM_ERROR";

interface CreateSampleRunRequest {
  problemId: number;
  language: "python";
  sourceCode: string;
  sampleIndex?: number;
  inputData?: string;
}

interface CreateSampleRunResponse {
  runId: number;
  status: SampleRunStatus;
}

export interface SampleRunResult {
  runId: number;
  problemId: number;
  sampleIndex: number;
  status: SampleRunStatus;
  input: string;
  expectedOutput: string;
  stdout: string | null;
  stderr: string | null;
  runtimeMs: number | null;
  memoryMb: number | null;
  message: string;
}

interface CreateExamAttemptRequest {
  roomCode: string;
  studentId: string;
  studentName: string;
  status: string;
}

interface RequestOptions {
  wakeBackend?: boolean;
}

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

async function wakeBackendIfConfigured() {
  if (!WAKE_API_URL) {
    return;
  }

  if (Date.now() - lastWakeAt < WAKE_REUSE_MS) {
    return;
  }

  if (!wakePromise) {
    wakePromise = fetch(WAKE_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason: "exam-request" }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Wake API ${response.status}`);
        }
        lastWakeAt = Date.now();
      })
      .finally(() => {
        wakePromise = null;
      });
  }

  return wakePromise;
}

function isTransientStartupStatus(status: number) {
  return status === 502 || status === 503 || status === 504;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  options: RequestOptions = {},
): Promise<T> {
  if (options.wakeBackend) {
    await wakeBackendIfConfigured();
  }

  const shouldRetryStartup = Boolean(options.wakeBackend && WAKE_API_URL);
  const maxAttempts = shouldRetryStartup ? STARTUP_RETRY_ATTEMPTS : 1;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
          "Content-Type": "application/json",
          ...init?.headers,
        },
        ...init,
      });

      if (response.ok) {
        return response.json() as Promise<T>;
      }

      if (!shouldRetryStartup || !isTransientStartupStatus(response.status)) {
        throw new Error(`API ${response.status}: ${path}`);
      }
    } catch (error) {
      if (!shouldRetryStartup || attempt === maxAttempts - 1) {
        throw error;
      }
    }

    await wait(Math.min(3000 + attempt * 2000, 10000));
  }

  throw new Error(`API startup timeout: ${path}`);
}

export async function fetchExams(): Promise<MockExam[]> {
  return request<MockExam[]>("/exams");
}

export async function createSubmission(
  payload: CreateSubmissionRequest,
): Promise<CreateSubmissionResponse> {
  return request<CreateSubmissionResponse>(
    "/submissions",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { wakeBackend: true },
  );
}

export async function getSubmission(submissionId: number): Promise<ProblemResult> {
  const response = await request<SubmissionResponse>(`/submissions/${submissionId}`);

  return {
    submissionId: response.submissionId,
    status: response.status,
    runtimeMs: response.runtimeMs ?? 0,
    memoryMb: response.memoryMb,
    passedCases: response.passedCases,
    totalCases: response.totalCases,
    message: response.errorMessage ?? response.message,
  };
}

export async function createSampleRun(
  payload: CreateSampleRunRequest,
): Promise<CreateSampleRunResponse> {
  return request<CreateSampleRunResponse>(
    "/runs",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { wakeBackend: true },
  );
}

export async function getSampleRun(runId: number): Promise<SampleRunResult> {
  return request<SampleRunResult>(`/runs/${runId}`);
}

export async function createExamAttempt(
  payload: CreateExamAttemptRequest,
): Promise<ExamHistory> {
  return request<ExamHistory>(
    "/exam-attempts",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { wakeBackend: true },
  );
}

export async function fetchExamAttempts(studentId: string): Promise<ExamHistory[]> {
  return request<ExamHistory[]>(
    `/exam-attempts?studentId=${encodeURIComponent(studentId)}`,
  );
}

export async function getReport(reportId: number): Promise<LlmReport> {
  return request<LlmReport>(`/reports/${reportId}`);
}
