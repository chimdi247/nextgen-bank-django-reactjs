import { Link } from "react-router-dom";
import { ArrowLeftRight, Banknote, CreditCard, FilePlus2, RefreshCw } from "lucide-react";
import { AccountCard } from "@/components/AccountCard";
import { TransactionList } from "@/components/TransactionList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts, fetchTransactions } from "@/lib/queries";

export default function Dashboard() {
  const { user } = useAuth();
  const accounts = useFetch(fetchAccounts);
  const txns = useFetch(() => fetchTransactions({}));
  const list = accounts.data ?? [];
  const totals = Object.entries(list.reduce<Record<string, number>>((m, a) => ({ ...m, [a.currency]: (m[a.currency] ?? 0) + Number(a.account_balance) }), {}));

  return (
    <>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-3xl font-semibold sm:text-4xl">Hello, {user?.first_name}</h1><p className="mt-1 text-sm text-muted-foreground">Here is where your money stands today.</p></div>
        <Button variant="outline" size="icon" onClick={() => { void accounts.reload(true); void txns.reload(true); }} aria-label="Refresh"><RefreshCw /></Button>
      </div>

      {accounts.error && <p className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{accounts.error}</p>}

      {accounts.loading ? <Skeleton className="h-56 rounded-2xl" /> : list.length === 0 ? (
        <Card className="border-dashed"><CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <FilePlus2 className="h-10 w-10 text-muted-foreground" />
          <h2 className="text-xl font-semibold">You do not have a bank account yet</h2>
          <p className="max-w-md text-sm text-muted-foreground">Complete your profile (photos, next of kin and the account you want) and we will open it automatically. An account executive then verifies your identity.</p>
          <Button asChild variant="accent"><Link to="/profile">Complete my profile</Link></Button>
        </CardContent></Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">{list.map((a) => <AccountCard key={a.id} account={a} holder={user?.full_name ?? ""} />)}</div>
      )}

      {totals.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-3">
          {totals.map(([cur, v]) => <div key={cur} className="rounded-lg border bg-card px-4 py-3"><p className="text-xs text-muted-foreground">Total · {cur.replace(/_/g, " ")}</p><p className="tnum font-display text-xl font-semibold">{money(v, cur as never)}</p></div>)}
        </div>
      )}

      <div className="mt-6 grid grid-cols-3 gap-3">
        <Button asChild variant="accent" size="lg" className="h-14 flex-col gap-1 text-sm"><Link to="/transfer"><ArrowLeftRight />Send</Link></Button>
        <Button asChild variant="outline" size="lg" className="h-14 flex-col gap-1 text-sm"><Link to="/withdraw"><Banknote />Withdraw</Link></Button>
        <Button asChild variant="outline" size="lg" className="h-14 flex-col gap-1 text-sm"><Link to="/cards"><CreditCard />Cards</Link></Button>
      </div>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between space-y-0"><CardTitle>Recent activity</CardTitle><Button asChild variant="ghost" size="sm"><Link to="/transactions">See all</Link></Button></CardHeader>
        <CardContent className="p-0"><TransactionList items={(txns.data?.results ?? []).slice(0, 6)} accounts={list} loading={txns.loading} empty="No activity yet. Send or receive money and it will show up here." /></CardContent>
      </Card>
    </>
  );
}
