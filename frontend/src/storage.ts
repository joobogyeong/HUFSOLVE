import type { ActiveExamDraft, StudentProfile } from "./types";

export const PROFILE_STORAGE_KEY = "hufsolve.studentProfile";
export const EXAM_DRAFT_STORAGE_KEY = "hufsolve.activeExamDraft";

function parseStored<T>(value: string | null): T | null {
  if (!value) {
    return null;
  }
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

export function readProfile(): StudentProfile | null {
  return parseStored<StudentProfile>(sessionStorage.getItem(PROFILE_STORAGE_KEY));
}

export function writeProfile(profile: StudentProfile | null) {
  if (profile) {
    sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
  } else {
    sessionStorage.removeItem(PROFILE_STORAGE_KEY);
  }
}

export function readExamDraft(): ActiveExamDraft | null {
  return parseStored<ActiveExamDraft>(localStorage.getItem(EXAM_DRAFT_STORAGE_KEY));
}

export function writeExamDraft(draft: ActiveExamDraft | null) {
  if (draft) {
    localStorage.setItem(EXAM_DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } else {
    localStorage.removeItem(EXAM_DRAFT_STORAGE_KEY);
  }
}
