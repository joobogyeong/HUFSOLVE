import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AlertCircle, Send, UserRound } from "lucide-react";
import { checkEmailVerified, sendEmailCode, verifyEmailCode } from "../api";
import { useApp } from "../AppContext";

export function LoginPage() {
  const { login, profile } = useApp();
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState("");
  const [studentName, setStudentName] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [verified, setVerified] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setVerified(false);
  }, [studentId, email]);

  if (profile) {
    return <Navigate to="/" replace />;
  }

  const sendCode = async () => {
    if (!studentId.trim() || !studentName.trim() || !email.trim()) {
      setNotice("학번, 이름, 학교 이메일을 모두 입력해주세요.");
      return;
    }
    try {
      await sendEmailCode({
        studentId: studentId.trim(),
        studentName: studentName.trim(),
        email: email.trim(),
      });
      setCodeSent(true);
      setNotice("인증번호가 발송되었습니다.");
    } catch {
      setNotice("인증번호 발송에 실패했습니다.");
    }
  };

  const verifyCode = async () => {
    try {
      const result = await verifyEmailCode({
        studentId: studentId.trim(),
        email: email.trim(),
        code: code.trim(),
      });
      setVerified(result.verified);
      setNotice(result.verified ? "학교 이메일 인증이 완료되었습니다." : "인증에 실패했습니다.");
    } catch {
      setNotice("인증번호가 일치하지 않거나 만료되었습니다.");
    }
  };

  const submit = async () => {
    if (!studentId.trim() || !studentName.trim() || !email.trim()) {
      setNotice("학번, 이름, 학교 이메일을 모두 입력해주세요.");
      return;
    }
    try {
      const isVerified =
        verified ||
        (
          await checkEmailVerified({
            studentId: studentId.trim(),
            email: email.trim(),
          })
        ).verified;
      if (!isVerified) {
        setNotice("학교 이메일 인증을 완료해주세요.");
        return;
      }
      login({ studentId: studentId.trim(), name: studentName.trim() });
      navigate("/", { replace: true });
    } catch {
      setNotice("학교 이메일 인증 여부를 확인할 수 없습니다.");
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-[radial-gradient(circle_at_top_left,_#ffffff_0,_#f7f7f5_34%,_#ececea_100%)] px-5 py-5">
      <section className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center py-12 text-center">
        <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/70 px-4 py-2 text-sm font-bold text-zinc-600">
          <UserRound className="h-4 w-4" />
          학생 로그인
        </div>
        <h1 className="text-5xl font-black sm:text-7xl">HUFSOLVE</h1>
        <div className="glass-panel mt-10 grid w-full gap-3 rounded-3xl p-5">
          <input value={studentId} onChange={(event) => setStudentId(event.target.value)} className="min-h-14 rounded-2xl border border-zinc-200 px-5 text-center font-bold" placeholder="학번" />
          <input value={studentName} onChange={(event) => setStudentName(event.target.value)} className="min-h-14 rounded-2xl border border-zinc-200 px-5 text-center font-bold" placeholder="이름" />
          <input value={email} onChange={(event) => setEmail(event.target.value)} className="min-h-14 rounded-2xl border border-zinc-200 px-5 text-center font-bold" placeholder="학교 이메일" />
          <button type="button" onClick={() => void sendCode()} className="min-h-14 rounded-2xl border border-zinc-300 bg-white font-bold">인증번호 발송</button>
          {codeSent && (
            <>
              <input value={code} onChange={(event) => setCode(event.target.value)} className="min-h-14 rounded-2xl border border-zinc-200 px-5 text-center font-bold" placeholder="인증번호" />
              <button type="button" onClick={() => void verifyCode()} className="min-h-14 rounded-2xl border border-zinc-300 bg-white font-bold">{verified ? "인증 완료" : "인증 확인"}</button>
            </>
          )}
          <button type="button" onClick={() => void submit()} className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-zinc-950 font-bold text-white">
            로그인 <Send className="h-4 w-4" />
          </button>
        </div>
        {notice && <div className="mt-5 flex w-full gap-2 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-left text-sm font-bold"><AlertCircle className="h-4 w-4 shrink-0" />{notice}</div>}
      </section>
    </main>
  );
}
