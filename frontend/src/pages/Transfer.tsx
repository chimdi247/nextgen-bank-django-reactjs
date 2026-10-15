import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ShieldQuestion, UserCheck } from "lucide-react";
import { toast } from "sonner";
import { ErrorNote, Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Steps } from "@/components/Steps";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CURRENCY, SECURITY_QUESTIONS, groupDigits, money } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts } from "@/lib/queries";
import type { LookupResult, Transaction } from "@/lib/types";

/** Three server-side steps: initiate -> security question -> e-mailed OTP. The server keeps the pending transfer in the session. */
export default function Transfer() {
  const { user } = useAuth();
  const accounts = useFetch(fetchAccounts);
  const usable = (accounts.data ?? []).filter((a) => a.fully_activated);
  const [step, setStep] = useState(0);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [answer, setAnswer] = useState("");
  const [otp, setOtp] = useState("");
  const [recipient, setRecipient] = useState<LookupResult | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; trace?: string } | null>(null);
  const [receipt, setReceipt] = useState<Transaction | null>(null);

  useEffect(() => { if (!from && usable[0]) setFrom(usable[0].account_number); }, [usable, from]);
  useEffect(() => {
    setRecipient(null); setLookupError(null);
    const n = to.replace(/\s/g, "");
    if (n.length < 12) return;
    let cancelled = false;
    api.get<LookupResult>("/accounts/lookup/", { account_number: n }).then((r) => !cancelled && setRecipient(r)).catch((e) => !cancelled && setLookupError(e instanceof Error ? e.message : "Account not found"));
    return () => { cancelled = true; };
  }, [to]);

  const source = usable.find((a) => a.account_number === from);
  const value = Number(amount);
  const tooMuch = !!source && value > Number(source.account_balance);
  const sameAcct = to.replace(/\s/g, "") === from;
  const currencyMismatch = !!recipient && !!source && recipient.currency !== source.currency;
  const canStart = !!source && !!recipient && recipient.is_active && value >= 0.1 && !tooMuch && !sameAcct && !currencyMismatch;
  const question = SECURITY_QUESTIONS.find((q) => q.value === user?.security_question)?.label ?? "Answer your security question";

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError(null);
    try { await fn(); } catch (e) { setError({ message: e instanceof Error ? e.message : "Something went wrong", trace: e instanceof ApiError ? e.traceId : undefined }); } finally { setBusy(false); }
  };
  const initiate = (e: FormEvent) => { e.preventDefault(); void run(async () => {
    await api.post("/accounts/transfer/initiate/", { sender_account: from, receiver_account: to.replace(/\s/g, ""), amount: value.toFixed(2), description: note.trim() || undefined });
    setStep(1);
  }); };
  const verifyAnswer = (e: FormEvent) => { e.preventDefault(); void run(async () => {
    await api.post("/accounts/transfer/verify-security-question/", { security_answer: answer });
    setStep(2); toast.success("We e-mailed you a one-time code to confirm the transfer.");
  }); };
  const confirm = (e: FormEvent) => { e.preventDefault(); void run(async () => {
    setReceipt(await api.post<Transaction>("/accounts/transfer/verify-otp/", { otp: otp.trim() }));
    setStep(3);
  }); };

  if (accounts.loading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!usable.length) return <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">You need an active, verified account to send money. <Link to="/profile" className="font-semibold text-foreground underline">Check your profile</Link>.</CardContent></Card>;

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Send money" description="Every transfer is confirmed with your security answer and an e-mailed one-time code." />
      <Steps steps={["Details", "Security question", "One-time code", "Done"]} current={step} />
      <Card><CardContent className="p-6">
        {step === 0 && (
          <form onSubmit={initiate} className="space-y-5">
            <Field id="from" label="From account">
              <Select id="from" value={from} onChange={(e) => setFrom(e.target.value)}>
                {usable.map((a) => <option key={a.id} value={a.account_number}>{groupDigits(a.account_number)} · {money(a.account_balance, a.currency)}</option>)}
              </Select>
            </Field>
            <Field id="to" label="Recipient account number">
              <Input id="to" inputMode="numeric" autoComplete="off" required value={to} onChange={(e) => setTo(e.target.value.replace(/[^\d\s]/g, ""))} className="font-mono tracking-wider" placeholder="1000 1100 0000 0015" />
              {recipient && !sameAcct && <p className="flex items-center gap-2 text-sm text-success"><UserCheck className="h-4 w-4" />{recipient.holder_name} · {CURRENCY[recipient.currency].code} {recipient.is_active ? "" : "· not yet active"}</p>}
              {sameAcct && <p className="text-sm text-destructive">That is the account you are sending from.</p>}
              {currencyMismatch && <p className="text-sm text-destructive">The recipient account is in {CURRENCY[recipient!.currency].code}; transfers must be in the same currency.</p>}
              {lookupError && <p className="text-sm text-destructive">{lookupError}</p>}
            </Field>
            <Field id="amount" label={`Amount (${source ? CURRENCY[source.currency].code : ""})`}>
              <Input id="amount" type="number" inputMode="decimal" step="0.01" min="0.1" required value={amount} onChange={(e) => setAmount(e.target.value)} className="tnum text-lg" placeholder="0.00" />
              <div className="flex flex-wrap gap-2">{[10, 50, 100, 500].map((v) => <button key={v} type="button" onClick={() => setAmount(String(v))} className="rounded-full border px-3 py-1 text-xs font-semibold hover:bg-secondary">{v}</button>)}</div>
              {tooMuch && <p className="text-sm text-destructive">That is more than your available balance.</p>}
            </Field>
            <Field id="note" label="Note (optional)"><Input id="note" maxLength={120} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Rent, dinner, thanks…" /></Field>
            <ErrorNote message={error?.message} traceId={error?.trace} />
            <Button type="submit" size="lg" variant="accent" className="w-full" disabled={!canStart} loading={busy}>Continue</Button>
          </form>
        )}
        {step === 1 && (
          <form onSubmit={verifyAnswer} className="space-y-5">
            <div className="flex items-start gap-3 rounded-lg bg-secondary/70 p-4"><ShieldQuestion className="mt-0.5 h-5 w-5 text-primary" /><div><p className="text-xs text-muted-foreground">Security question</p><p className="font-semibold">{question}</p></div></div>
            <Field id="ans" label="Your answer"><Input id="ans" required autoFocus maxLength={30} value={answer} onChange={(e) => setAnswer(e.target.value)} autoComplete="off" /></Field>
            <ErrorNote message={error?.message} traceId={error?.trace} />
            <Button type="submit" size="lg" className="w-full" loading={busy}>Send me the code</Button>
          </form>
        )}
        {step === 2 && (
          <form onSubmit={confirm} className="space-y-5">
            <p className="text-sm text-muted-foreground">Enter the 6-digit code we e-mailed you to authorise sending <b className="text-foreground">{money(value, source?.currency)}</b> to <b className="text-foreground">{recipient?.holder_name}</b>.</p>
            <Field id="otp" label="One-time code"><Input id="otp" inputMode="numeric" maxLength={6} autoFocus required value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} className="h-14 text-center font-mono text-2xl tracking-[0.5em]" placeholder="••••••" /></Field>
            <ErrorNote message={error?.message} traceId={error?.trace} />
            <Button type="submit" size="lg" variant="accent" className="w-full" loading={busy} disabled={otp.length !== 6}>Confirm transfer</Button>
          </form>
        )}
        {step === 3 && receipt && (
          <div className="space-y-4 text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-success" />
            <h2 className="text-2xl font-semibold">Money sent</h2>
            <p className="tnum font-display text-4xl font-semibold">{money(receipt.amount, source?.currency)}</p>
            <p className="text-sm text-muted-foreground">to {receipt.receiver} · {groupDigits(receipt.receiver_account ?? "")}</p>
            <p className="rounded-md bg-secondary px-3 py-2 font-mono text-xs">Reference {receipt.id}</p>
            <div className="flex gap-3 pt-2">
              <Button variant="outline" className="flex-1" onClick={() => { setStep(0); setTo(""); setAmount(""); setNote(""); setAnswer(""); setOtp(""); setReceipt(null); void accounts.reload(true); }}>Send another</Button>
              <Button asChild className="flex-1"><Link to="/">Back to overview</Link></Button>
            </div>
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
