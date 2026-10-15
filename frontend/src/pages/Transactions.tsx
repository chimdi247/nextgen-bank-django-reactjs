import { useState } from "react";
import { FileDown } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { TransactionList } from "@/components/TransactionList";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { groupDigits } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts, fetchTransactions } from "@/lib/queries";

const SIZE = 10;

export default function Transactions() {
  const accounts = useFetch(fetchAccounts);
  const [account, setAccount] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);

  const txns = useFetch(
    () => fetchTransactions({ page: page + 1, page_size: SIZE, account_number: account, start_date: start, end_date: end ? `${end}T23:59:59` : "", ordering }),
    [page, account, start, end, ordering],
  );
  const reset = (fn: () => void) => { fn(); setPage(0); };
  const pages = Math.max(1, Math.ceil((txns.data?.count ?? 0) / SIZE));

  const requestPdf = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ message: string }>("/accounts/transactions/pdf/", { account_number: account || undefined, start_date: start || undefined, end_date: end || undefined });
      toast.success(r?.message ?? "Your statement is being generated and will be e-mailed to you.");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Could not request the statement"); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Transactions" description="Everything that moved on your accounts." actions={<Button variant="outline" onClick={requestPdf} loading={busy}><FileDown />E-mail PDF statement</Button>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="w-64"><Select value={account} onChange={(e) => reset(() => setAccount(e.target.value))} aria-label="Account"><option value="">All accounts</option>{(accounts.data ?? []).map((a) => <option key={a.id} value={a.account_number}>{groupDigits(a.account_number)}</option>)}</Select></div>
        <Input type="date" className="w-40" value={start} onChange={(e) => reset(() => setStart(e.target.value))} aria-label="From date" />
        <Input type="date" className="w-40" value={end} onChange={(e) => reset(() => setEnd(e.target.value))} aria-label="To date" />
        <div className="w-44"><Select value={ordering} onChange={(e) => reset(() => setOrdering(e.target.value))} aria-label="Sort"><option value="-created_at">Newest first</option><option value="created_at">Oldest first</option><option value="-amount">Largest first</option><option value="amount">Smallest first</option></Select></div>
      </div>
      {txns.error && <p className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{txns.error}</p>}
      <Card>
        <TransactionList items={txns.data?.results ?? []} accounts={accounts.data ?? []} loading={txns.loading} empty="No transactions match your filters." />
        <Pagination page={page} pages={pages} total={txns.data?.count ?? 0} onChange={setPage} />
      </Card>
    </>
  );
}
