export type Screen = "login" | "home" | "exam" | "my";

export type JudgeStatus = "UNSUBMITTED" | "ACCEPTED" | "WRONG_ANSWER";

export type ExamType = "중간고사" | "기말고사";

export interface SampleCase {
  input: string;
  output: string;
}

export interface Problem {
  id: number;
  title: string;
  level: "Easy" | "Medium" | "Hard";
  points: number;
  timeLimitMs: number;
  memoryLimitMb: number;
  description: string[];
  inputDescription: string;
  outputDescription: string;
  constraints: string[];
  samples: SampleCase[];
  starterCode: string;
}

export interface MockExam {
  roomCode: string;
  title: string;
  course: string;
  professor: string;
  examType: ExamType;
  durationSeconds: number;
  startsAt: string;
  problems: Problem[];
}

export interface ProblemResult {
  status: JudgeStatus;
  runtimeMs: number;
  memoryMb: number;
  passedCases: number;
  totalCases: number;
  message: string;
}

export interface ExamHistory {
  id: string;
  title: string;
  roomCode: string;
  submittedAt: string;
  score: number;
  passedProblems: number;
  totalProblems: number;
  status: string;
}

export interface StudentProfile {
  studentId: string;
  name: string;
}
