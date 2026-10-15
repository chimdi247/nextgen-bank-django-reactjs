import { ArrowDownLeft, ArrowUpRight, Inbox } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { describeTx, money, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Account, Transaction } from "@/lib/types";

export function TransactionList({ items, accounts, loading, empty = "No transactions yet." }: { items: Transaction[]; accounts: Account[]; loading?: boolean; empty?: string }) {
  if (loading) return <div className="divide-y">{[0, 1, 2, 3].map((i) => <div key={i} className="flex items-center gap-3 p-4"><Skeleton className="h-10 w-10 rounded-full" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-1/2" /><Skeleton className="h-3 w-1/3" /></div><Skeleton className="h-5 w-16" /></div>)}</div>;
  if (!items.length) return <div className="flex flex-col items-center gap-2 px-4 py-12 text-center text-muted-foreground"><Inbox className="h-8 w-8" /><p className="text-sm">{empty}</p></div>;
  return (
    <ul className="divide-y">
      {items.map((t) => {
        const d = describeTx(t, accounts);
        const Icon = d.debit ? ArrowUpRight : ArrowDownLeft;
        return (
          <li key={t.id} className="flex items-center gap-3 px-4 py-3.5">
            <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-full", d.debit ? "bg-destructive/10 text-destructive" : "bg-success/10 text-success")}><Icon className="h-5 w-5" /></span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{d.label}</span>
              <span className="block truncate text-xs text-muted-foreground">{shortDate(t.created_at)} · {t.description || t.transaction_type}</span>
            </span>
            {t.status !== "completed" && <StatusBadge status={t.status} />}
            <span className={cn("tnum text-sm font-semibold", d.debit ? "text-foreground" : "text-success")}>{d.debit ? "−" : "+"}{money(t.amount, d.currency)}</span>
          </li>
        );
      })}
    </ul>
  );
}
