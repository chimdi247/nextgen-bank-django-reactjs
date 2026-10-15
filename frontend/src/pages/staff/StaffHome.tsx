import { Link } from "react-router-dom";
import { FileCheck2, HandCoins, Landmark, Lock, UserPlus, Users } from "lucide-react";
import { StatCard } from "@/components/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CURRENCY, money, titleCase } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { BankStats } from "@/lib/types";

export default function StaffHome() {
  const { user, hasRole } = useAuth();
  const manager = hasRole("branch_manager");
  const stats = useFetch(() => api.get<BankStats>("/accounts/stats/"), [], manager);
  const s = stats.data;
  return (
    <>
      <div className="mb-7"><h1 className="text-3xl font-semibold sm:text-4xl">Branch overview</h1><p className="mt-1 text-sm text-muted-foreground">Signed in as {user?.full_name} · {titleCase(user?.role)}</p></div>
      {manager ? (
        <>
          {stats.error && <p className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{stats.error}</p>}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Customers" value={s?.customers ?? 0} icon={Users} loading={stats.loading} hint={`${s?.new_customers_7d ?? 0} new in 7 days`} />
            <StatCard label="Bank accounts" value={s?.accounts_total ?? 0} icon={Landmark} loading={stats.loading} />
            <StatCard label="Awaiting KYC" value={s?.accounts_pending_kyc ?? 0} icon={FileCheck2} loading={stats.loading} />
            <StatCard label="Locked users" value={s?.locked_users ?? 0} icon={Lock} loading={stats.loading} />
          </div>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <Card><CardHeader><CardTitle>Balances held</CardTitle></CardHeader><CardContent className="space-y-3">
              {(s?.balances ?? []).length === 0 && <p className="text-sm text-muted-foreground">No accounts yet.</p>}
              {(s?.balances ?? []).map((b) => <div key={b.currency} className="flex items-center justify-between"><span className="text-sm text-muted-foreground">{CURRENCY[b.currency]?.label} · {b.accounts} accounts</span><span className="tnum font-display text-xl font-semibold">{money(b.total, b.currency)}</span></div>)}
            </CardContent></Card>
            <Card><CardHeader><CardTitle>Completed in the last 24 h</CardTitle></CardHeader><CardContent className="space-y-3">
              {(s?.transactions_24h ?? []).length === 0 && <p className="text-sm text-muted-foreground">Nothing yet.</p>}
              {(s?.transactions_24h ?? []).map((t) => <div key={t.type} className="flex items-center justify-between"><span className="text-sm">{titleCase(t.type)}</span><span className="tnum text-sm"><b>{t.count}</b> · {Number(t.amount).toLocaleString()}</span></div>)}
            </CardContent></Card>
          </div>
        </>
      ) : <Card><CardContent className="p-8 text-sm text-muted-foreground">Use the menu to start your work. Branch-wide statistics are available to branch managers.</CardContent></Card>}
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {hasRole("teller") && <Button asChild variant="accent" size="lg" className="h-14"><Link to="/staff/deposit"><HandCoins />Cash deposit</Link></Button>}
        {hasRole("account_executive") && <Button asChild variant="outline" size="lg" className="h-14"><Link to="/staff/kyc"><FileCheck2 />KYC verification</Link></Button>}
        {manager && <Button asChild variant="outline" size="lg" className="h-14"><Link to="/staff/customers"><UserPlus />Customers</Link></Button>}
      </div>
    </>
  );
}
