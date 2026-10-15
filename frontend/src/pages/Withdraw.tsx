import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, UserRound } from "lucide-react";
import { ErrorNote, Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Steps } from "@/components/Steps";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CURRENCY, groupDigits, money } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts } from "@/lib/queries";

/** Two server-side steps: initiate -> confirm with your username. */
export default function Withdraw() {
  const { user } = useAuth();
  const accounts = useFetch(fetchAccounts);
  const usable = (accounts.data ?? []).filter((a) => a.fully_activated);
  const [step, setStep] = useState(0);
  const [acct, setAcct] = useState("");
  const [amount, setAmount] = useState("");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; trace?: string } | null>(null);

  useEffect(() => { if (!acct && usable[0]) setAcct(usable[0].account_number); }, [usable, acct]);
  const source = usable.find((a) => a.account_number === acct);
  const value = Number(amount);
  const tooMuch = !!source && value > Number(source.account_balance);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError(null);
    try { await fn(); } catch (e) { setError({ message: e instanceof Error ? e.message : "Something went wrong", trace: e instanceof ApiError ? e.traceId : undefined }); } finally { setBusy(false); }
  };
  const initiate = (e: FormEvent) => { e.preventDefault(); void run(async () => { await api.post("/accounts/initiate-withdrawal/", { account_number: acct, amount: value.toFixed(2) }); setStep(1); }); };
  const confirm = (e: FormEvent) => { e.preventDefault(); void run(async () => { await api.post("/accounts/verify-username-and-withdraw/", { username: username.trim() }); setStep(2); }); };

  if (!accounts.loading && !usable.length) return <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">You need an active, verified account to withdraw. <Link to="/profile" className="font-semibold text-foreground underline">Check your profile</Link>.</CardContent></Card>;

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Withdraw cash" description="Confirm with your username to release the funds." />
      <Steps steps={["Amount", "Confirm", "Done"]} current={step} />
      <Card><CardContent className="p-6">
        {step === 0 && (
          <form onSubmit={initiate} className="space-y-5">
            <Field id="acct" label="From account"><Select id="acct" value={acct} onChange={(e) => setAcct(e.target.value)}>{usable.map((a) => <option key={a.id} value={a.account_number}>{groupDigits(a.account_number)} · {money(a.account_balance, a.currency)}</option>)}</Select></Field>
            <Field id="amt" label={`Amount (${source ? CURRENCY[source.currency].code : ""})`}>
              <Input id="amt" type="number" step="0.01" min="0.1" required value={amount} onChange={(e) => setAmount(e.target.value)} className="tnum text-lg" placeholder="0.00" />
              {tooMuch && <p className="text-sm text-destructive">That is more than your available balance.</p>}
            </Field>
            <ErrorNote message={error?.message} traceId={error?.trace} />
            <Button type="submit" size="lg" className="w-full" loading={busy} disabled={!source || value < 0.1 || tooMuch}>Continue</Button>
          </form>
        )}
        {step === 1 && (
          <form onSubmit={confirm} className="space-y-5">
            <div className="flex items-start gap-3 rounded-lg bg-secondary/70 p-4"><UserRound className="mt-0.5 h-5 w-5 text-primary" /><p className="text-sm">Type your account <b>username</b> to confirm withdrawing <b>{money(value, source?.currency)}</b>. You can find it on the Profile page{user?.username ? <> (it starts with <span className="font-mono">{user.username.slice(0, 3)}</span>)</> : null}.</p></div>
            <Field id="un" label="Username"><Input id="un" required autoFocus maxLength={12} value={username} onChange={(e) => setUsername(e.target.value)} className="font-mono" autoComplete="off" /></Field>
            <ErrorNote message={error?.message} traceId={error?.trace} />
            <Button type="submit" size="lg" className="w-full" loading={busy}>Withdraw {money(value, source?.currency)}</Button>
          </form>
        )}
        {step === 2 && (
          <div className="space-y-4 text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-success" />
            <h2 className="text-2xl font-semibold">Withdrawal complete</h2>
            <p className="tnum font-display text-4xl font-semibold">{money(value, source?.currency)}</p>
            <Button asChild className="w-full"><Link to="/">Back to overview</Link></Button>
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
