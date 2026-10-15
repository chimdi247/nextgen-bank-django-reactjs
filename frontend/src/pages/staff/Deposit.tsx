import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, UserCheck } from "lucide-react";
import { ErrorNote, Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatErr } from "@/lib/errors";
import { groupDigits, money } from "@/lib/format";

interface Customer { account_number: string; full_name: string; email: string; currency?: never; [k: string]: unknown }

export default function Deposit() {
  const [number, setNumber] = useState("");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    setCustomer(null); setLookupError(null);
    const n = number.replace(/\s/g, "");
    if (n.length < 12) return;
    let cancelled = false;
    api.get<Customer>("/accounts/deposit/", { account_number: n }).then((c) => !cancelled && setCustomer(c)).catch((e) => !cancelled && setLookupError(formatErr(e)));
    return () => { cancelled = true; };
  }, [number]);

  const value = Number(amount);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { await api.post("/accounts/deposit/", { account_number: number.replace(/\s/g, ""), amount: value.toFixed(2) }); setDone(money(value)); }
    catch (err) { setError(formatErr(err)); } finally { setBusy(false); }
  };

  if (done) return (
    <div className="mx-auto max-w-md"><Card className="text-center"><CardContent className="space-y-4 p-8">
      <CheckCircle2 className="mx-auto h-14 w-14 text-success" /><h1 className="text-2xl font-semibold">Deposit recorded</h1>
      <p className="tnum font-display text-4xl font-semibold">{done}</p><p className="text-sm text-muted-foreground">into {groupDigits(number.replace(/\s/g, ""))}. The customer receives an e-mail receipt.</p>
      <Button className="w-full" onClick={() => { setDone(null); setNumber(""); setAmount(""); }}>Make another deposit</Button>
    </CardContent></Card></div>
  );

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Cash deposit" description="Credit a customer account over the counter." />
      <Card><CardContent className="p-6"><form onSubmit={submit} className="space-y-5">
        <Field id="acct" label="Account number">
          <Input id="acct" inputMode="numeric" required autoComplete="off" value={number} onChange={(e) => setNumber(e.target.value.replace(/[^\d\s]/g, ""))} className="font-mono tracking-wider" />
          {customer && <p className="flex items-center gap-2 text-sm text-success"><UserCheck className="h-4 w-4" />{customer.full_name} · {customer.email}</p>}
          {lookupError && <p className="text-sm text-destructive">{lookupError}</p>}
        </Field>
        <Field id="amt" label="Amount"><Input id="amt" type="number" step="0.01" min="0.1" required value={amount} onChange={(e) => setAmount(e.target.value)} className="tnum text-lg" placeholder="0.00" /></Field>
        <ErrorNote message={error} />
        <Button type="submit" size="lg" variant="accent" className="w-full" loading={busy} disabled={!customer || value < 0.1}>{value >= 0.1 ? `Deposit ${money(value)}` : "Deposit"}</Button>
      </form></CardContent></Card>
    </div>
  );
}
