import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, MailOpen } from "lucide-react";
import { toast } from "sonner";
import { AuthShell } from "./AuthShell";
import { ErrorNote, Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const MAILPIT = (import.meta.env.VITE_MAILPIT_URL as string | undefined) ?? "http://localhost:8025";

export default function Login() {
  const { requestOtp, verifyOtp } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<"password" | "otp">("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; trace?: string } | null>(null);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => { if (cooldown <= 0) return; const t = setTimeout(() => setCooldown((c) => c - 1), 1000); return () => clearTimeout(t); }, [cooldown]);

  const fail = (e: unknown) => { const a = e instanceof ApiError ? e : null; setError({ message: e instanceof Error ? e.message : "Something went wrong", trace: a?.traceId }); };

  const sendCode = async (e?: FormEvent) => {
    e?.preventDefault();
    setBusy(true); setError(null);
    try { await requestOtp(email.trim(), password); setStep("otp"); setCooldown(30); toast.success("We sent a 6-digit code to your e-mail."); }
    catch (err) { fail(err); } finally { setBusy(false); }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await verifyOtp(email.trim(), otp.trim()); navigate("/", { replace: true }); }
    catch (err) { fail(err); } finally { setBusy(false); }
  };

  if (step === "otp") {
    return (
      <AuthShell title="Enter your code" subtitle={`We e-mailed a 6-digit code to ${email}. It is valid for a few minutes.`}>
        <form onSubmit={verify} className="space-y-4">
          <Field id="otp" label="One-time code">
            <Input id="otp" inputMode="numeric" autoComplete="one-time-code" autoFocus required maxLength={6} pattern="\d{6}" value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} className="h-14 text-center font-mono text-2xl tracking-[0.5em]" placeholder="••••••" />
          </Field>
          <ErrorNote message={error?.message} traceId={error?.trace} />
          <Button type="submit" size="lg" className="w-full" loading={busy} disabled={otp.length !== 6}>Verify and sign in</Button>
          <div className="flex items-center justify-between text-sm">
            <button type="button" onClick={() => { setStep("password"); setOtp(""); setError(null); }} className="flex items-center gap-1 text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />Back</button>
            <button type="button" disabled={cooldown > 0 || busy} onClick={() => void sendCode()} className="font-semibold disabled:text-muted-foreground">{cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}</button>
          </div>
        </form>
        <a href={MAILPIT} target="_blank" rel="noreferrer" className="mt-6 flex items-start gap-3 rounded-lg border border-dashed p-3 text-xs text-muted-foreground hover:bg-secondary">
          <MailOpen className="mt-0.5 h-4 w-4 shrink-0" />
          <span><b className="text-foreground">Local environment:</b> e-mails are caught by Mailpit. Open it to read your code <ExternalLink className="inline h-3 w-3" /></span>
        </a>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your account. We will e-mail you a one-time code next.">
      <form onSubmit={sendCode} className="space-y-4">
        <Field id="email" label="Email"><Input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></Field>
        <Field id="password" label="Password"><Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <ErrorNote message={error?.message} traceId={error?.trace} />
        <Button type="submit" size="lg" className="w-full" loading={busy}>Continue</Button>
        <div className="text-right text-sm"><Link to="/forgot-password" className="text-muted-foreground underline-offset-4 hover:underline">Forgot password?</Link></div>
      </form>
      <button type="button" onClick={() => { setEmail("admin@example.com"); setPassword("password123"); }}
        className="mt-4 w-full rounded-md border border-dashed px-3 py-2.5 text-left text-xs text-muted-foreground hover:bg-secondary">
        Local demo: fill in the seeded administrator (admin@example.com)
      </button>
      <p className="mt-8 text-center text-sm text-muted-foreground">New here? <Link to="/register" className="font-semibold text-foreground underline underline-offset-4">Open an account</Link></p>
    </AuthShell>
  );
}
