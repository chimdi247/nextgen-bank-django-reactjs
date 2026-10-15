import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { AuthShell } from "./AuthShell";
import { ErrorNote, Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try { await api.post("/auth/users/reset_password/", { email: email.trim() }); setSent(true); }
    catch { setSent(true); }   // never reveal whether the address exists
    finally { setBusy(false); }
  };
  return (
    <AuthShell title="Reset your password" subtitle="Enter your e-mail and we will send you a reset link.">
      {sent ? <p className="rounded-lg border bg-card p-5 text-sm">If an account exists for <b>{email}</b>, a reset link is on its way.</p> : (
        <form onSubmit={submit} className="space-y-4">
          <Field id="email" label="Email"><Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Button type="submit" size="lg" className="w-full" loading={busy}>Send reset link</Button>
        </form>
      )}
      <p className="mt-8 text-center text-sm"><Link to="/login" className="font-semibold underline underline-offset-4">Back to sign in</Link></p>
    </AuthShell>
  );
}

export function ResetPassword() {
  const { uid, token } = useParams();
  const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null); const [done, setDone] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (pw !== pw2) { setError("The passwords do not match."); return; }
    setBusy(true); setError(null);
    try { await api.post("/auth/users/reset_password_confirm/", { uid, token, new_password: pw, re_new_password: pw2 }); setDone(true); toast.success("Password updated"); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not reset the password"); }
    finally { setBusy(false); }
  };
  return (
    <AuthShell title="Choose a new password" subtitle="Use at least 8 characters.">
      {done ? <Button asChild size="lg" className="w-full"><Link to="/login">Sign in</Link></Button> : (
        <form onSubmit={submit} className="space-y-4">
          <Field id="pw" label="New password"><Input id="pw" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
          <Field id="pw2" label="Repeat new password"><Input id="pw2" type="password" required minLength={8} value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" /></Field>
          <ErrorNote message={error} />
          <Button type="submit" size="lg" className="w-full" loading={busy}>Update password</Button>
        </form>
      )}
    </AuthShell>
  );
}
