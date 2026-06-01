import type { ExamHistory, JudgeStatus, MockExam, ProblemResult } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchExams(): Promise<MockExam[]> {
  return request<MockExam[]>("/exams");
}

export async function createSubmission(
  payload: CreateSubmissionRequest,
): Promise<CreateSubmissionResponse> {
  return request<CreateSubmissionResponse>("/submissions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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
  return request<CreateSampleRunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSampleRun(runId: number): Promise<SampleRunResult> {
  return request<SampleRunResult>(`/runs/${runId}`);
}

export async function createExamAttempt(
  payload: CreateExamAttemptRequest,
): Promise<ExamHistory> {
  return request<ExamHistory>("/exam-attempts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchExamAttempts(studentId: string): Promise<ExamHistory[]> {
  return request<ExamHistory[]>(
    `/exam-attempts?studentId=${encodeURIComponent(studentId)}`,
  );
}
