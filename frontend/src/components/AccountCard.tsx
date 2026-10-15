import { useState } from "react";
import { Check, Copy, Eye, EyeOff } from "lucide-react";
import { BrandMark } from "@/components/Brand";
import { StatusBadge } from "@/components/StatusBadge";
import { CURRENCY, groupDigits, money, titleCase } from "@/lib/format";
import type { Account } from "@/lib/types";

/** The account as a physical card: the one memorable object of the UI. */
export function AccountCard({ account, holder }: { account: Account; holder: string }) {
  const [hidden, setHidden] = useState(false);
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(account.account_number); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* clipboard unavailable */ }
  };
  const state = account.fully_activated ? "active" : account.kyc_verified ? "pending" : "pending";
  return (
    <div className="card-sheen relative overflow-hidden rounded-2xl bg-primary p-6 text-primary-foreground shadow-lg">
      <div className="relative flex items-start justify-between">
        <BrandMark />
        <div className="[&>div]:bg-white/10 [&>div]:text-white">
          <StatusBadge status={state} />
        </div>
      </div>
      <p className="relative mt-7 text-sm text-white/60">{titleCase(account.account_type)} account · {CURRENCY[account.currency].code}</p>
      <div className="relative mt-1 flex items-center gap-3">
        <p className="tnum font-display text-4xl font-semibold tracking-tight">{hidden ? "••••••" : money(account.account_balance, account.currency)}</p>
        <button onClick={() => setHidden((h) => !h)} className="rounded-md p-1.5 text-white/60 hover:bg-white/10 hover:text-white" aria-label={hidden ? "Show balance" : "Hide balance"}>
          {hidden ? <Eye className="h-5 w-5" /> : <EyeOff className="h-5 w-5" />}
        </button>
      </div>
      <div className="relative mt-7 flex items-end justify-between gap-3">
        <div className="min-w-0"><p className="text-xs text-white/50">Account holder</p><p className="truncate font-medium">{holder}</p></div>
        <button onClick={copy} className="tnum flex items-center gap-2 font-mono text-sm tracking-wider hover:text-accent" aria-label="Copy account number">
          {groupDigits(account.account_number)}{copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4 opacity-60" />}
        </button>
      </div>
      {!account.fully_activated && (
        <p className="relative mt-4 rounded-md bg-white/10 px-3 py-2 text-xs text-white/80">
          {account.kyc_verified ? "Verification complete, activating." : "Awaiting identity (KYC) verification by an account executive. You can receive money once it is verified."}
        </p>
      )}
    </div>
  );
}
