import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { AuthShell } from "./AuthShell";
import { ErrorNote, Field } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { SECURITY_QUESTIONS } from "@/lib/format";

export default function Register() {
  const [f, setF] = useState({ first_name: "", last_name: "", email: "", id_no: "", security_question: SECURITY_QUESTIONS[0].value, security_answer: "", password: "", re_password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; trace?: string } | null>(null);
  const [done, setDone] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF((p) => ({ ...p, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (f.password !== f.re_password) { setError({ message: "The passwords do not match." }); return; }
    setBusy(true); setError(null);
    try {
      await api.post("/auth/users/", { ...f, email: f.email.trim(), id_no: Number(f.id_no) });
      setDone(true);
    } catch (err) {
      setError({ message: err instanceof Error ? err.message : "Could not create the account", trace: err instanceof ApiError ? err.traceId : undefined });
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <AuthShell title="Check your inbox" subtitle="One more step before you can sign in.">
        <div className="rounded-lg border bg-card p-5 text-sm">
          <MailCheck className="mb-3 h-8 w-8 text-success" />
          <p>We sent an activation link to <b>{f.email}</b>. Open it to activate your account, then sign in.</p>
          <p className="mt-3 text-xs text-muted-foreground">Local environment: the e-mail is in Mailpit (port 8025).</p>
        </div>
        <Button asChild size="lg" className="mt-6 w-full"><Link to="/login">Back to sign in</Link></Button>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Open your account" subtitle="Create your profile first, then complete KYC to open a bank account.">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field id="fn" label="First name"><Input id="fn" required maxLength={30} value={f.first_name} onChange={set("first_name")} autoComplete="given-name" /></Field>
          <Field id="ln" label="Last name"><Input id="ln" required maxLength={30} value={f.last_name} onChange={set("last_name")} autoComplete="family-name" /></Field>
        </div>
        <Field id="em" label="Email"><Input id="em" type="email" required value={f.email} onChange={set("email")} autoComplete="email" /></Field>
        <Field id="idn" label="National ID number" hint="Digits only; it must be unique."><Input id="idn" inputMode="numeric" required value={f.id_no} onChange={set("id_no")} /></Field>
        <Field id="sq" label="Security question" hint="You will be asked this before every transfer.">
          <Select id="sq" value={f.security_question} onChange={set("security_question")}>{SECURITY_QUESTIONS.map((q) => <option key={q.value} value={q.value}>{q.label}</option>)}</Select>
        </Field>
        <Field id="sa" label="Security answer"><Input id="sa" required maxLength={30} value={f.security_answer} onChange={set("security_answer")} autoComplete="off" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field id="pw" label="Password"><Input id="pw" type="password" required minLength={8} value={f.password} onChange={set("password")} autoComplete="new-password" /></Field>
          <Field id="pw2" label="Repeat password"><Input id="pw2" type="password" required minLength={8} value={f.re_password} onChange={set("re_password")} autoComplete="new-password" /></Field>
        </div>
        <ErrorNote message={error?.message} traceId={error?.trace} />
        <Button type="submit" size="lg" className="w-full" loading={busy}>Create account</Button>
      </form>
      <p className="mt-8 text-center text-sm text-muted-foreground">Already a customer? <Link to="/login" className="font-semibold text-foreground underline underline-offset-4">Sign in</Link></p>
    </AuthShell>
  );
}
