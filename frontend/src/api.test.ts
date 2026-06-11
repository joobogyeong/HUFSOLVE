import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";


beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_API_BASE_URL", "/api");
  vi.stubEnv("VITE_WAKE_API_URL", "https://wake.example.com/wake");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("fetchExams", () => {
  it("wakes the backend before loading exams", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    const { fetchExams } = await import("./api");
    await expect(fetchExams()).resolves.toEqual([]);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "https://wake.example.com/wake",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/exams",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });
});

describe("authentication", () => {
  it("wakes the backend before sending an email verification code", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ message: "sent" }) });
    vi.stubGlobal("fetch", fetchMock);

    const { sendEmailCode } = await import("./api");
    await expect(
      sendEmailCode({
        studentId: "202600001",
        studentName: "Demo Student",
        email: "202600001@hufs.ac.kr",
      }),
    ).resolves.toEqual({ message: "sent" });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "https://wake.example.com/wake",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/auth/send-code",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
