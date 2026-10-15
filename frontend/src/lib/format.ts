import type { Account, Currency, Transaction } from "./types";

export const CURRENCY: Record<Currency, { code: string; label: string; symbol: string }> = {
  us_dollar: { code: "USD", label: "US Dollar", symbol: "$" },
  pound_sterling: { code: "GBP", label: "Pound Sterling", symbol: "£" },
  kenya_shilling: { code: "KES", label: "Kenya Shilling", symbol: "KSh" },
};

export function money(value: string | number | undefined | null, currency: Currency = "us_dollar") {
  const n = typeof value === "string" ? Number(value) : value ?? 0;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: CURRENCY[currency]?.code ?? "USD" }).format(Number.isFinite(n) ? n : 0);
}

export function dateTime(iso?: string | null) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function shortDate(iso?: string | null) {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/** 1000 1100 0000 0015 style grouping for 16-digit account / card numbers. */
export function groupDigits(n?: string, size = 4) {
  return (n ?? "").replace(new RegExp(`(.{${size}})`, "g"), "$1 ").trim();
}
export const maskCard = (n: string) => `•••• •••• •••• ${n.slice(-4)}`;

export function initials(name?: string) {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase() || "?";
}

export const titleCase = (s?: string | null) => (s ?? "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

/** What a transaction means for the signed-in customer: money in or out, and with whom. */
export function describeTx(t: Transaction, mine: Account[]) {
  const own = new Set(mine.map((a) => a.account_number));
  let debit: boolean;
  if (t.transaction_type === "withdrawal") debit = true;
  else if (t.transaction_type === "deposit" || t.transaction_type === "interest") debit = false;
  else debit = !!t.sender_account && own.has(t.sender_account);
  const label =
    t.transaction_type === "transfer" ? (debit ? `Transfer to ${t.receiver ?? t.receiver_account}` : `Transfer from ${t.sender ?? t.sender_account}`)
    : t.transaction_type === "deposit" ? "Cash deposit"
    : t.transaction_type === "withdrawal" ? "Cash withdrawal"
    : "Interest";
  const account = (debit ? t.sender_account : t.receiver_account) ?? undefined;
  const currency = mine.find((a) => a.account_number === account)?.currency ?? mine[0]?.currency ?? "us_dollar";
  return { debit, label, currency };
}

export const SECURITY_QUESTIONS = [
  { value: "maiden_name", label: "What is your mother's maiden name?" },
  { value: "favorite_color", label: "What is your favorite color?" },
  { value: "birth_city", label: "What is the city where you were born?" },
  { value: "childhood_friend", label: "What is the name of your childhood best friend?" },
];
