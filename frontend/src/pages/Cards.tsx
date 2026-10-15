import { useState } from "react";
import { Eye, EyeOff, Plus, Trash2, Wifi } from "lucide-react";
import { toast } from "sonner";
import { Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { groupDigits, money, titleCase } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts, fetchCards } from "@/lib/queries";
import type { VirtualCard } from "@/lib/types";

function CardFace({ card }: { card: VirtualCard }) {
  const [show, setShow] = useState(false);
  return (
    <div className="card-sheen relative aspect-[1.586/1] w-full overflow-hidden rounded-2xl bg-primary p-5 text-primary-foreground shadow-lg">
      <div className="flex items-start justify-between"><span className="font-display text-lg font-semibold">NextGen</span><Wifi className="h-6 w-6 rotate-90 text-white/60" /></div>
      <p className="tnum mt-7 font-mono text-xl tracking-widest">{show ? groupDigits(card.card_number) : `•••• •••• •••• ${card.card_number.slice(-4)}`}</p>
      <div className="mt-5 flex items-end justify-between text-xs">
        <div><p className="text-white/50">Expires</p><p className="font-mono text-sm">{new Date(card.expiry_date).toLocaleDateString("en-GB", { month: "2-digit", year: "2-digit" })}</p></div>
        <div><p className="text-white/50">CVV</p><p className="font-mono text-sm">{show ? card.cvv : "•••"}</p></div>
        <div className="text-right"><p className="text-white/50">Balance</p><p className="tnum font-display text-lg font-semibold">{money(card.balance)}</p></div>
      </div>
      <button onClick={() => setShow((s) => !s)} className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-white/10 p-1.5 hover:bg-white/20" aria-label={show ? "Hide card details" : "Show card details"}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
    </div>
  );
}

export default function Cards() {
  const cards = useFetch(fetchCards);
  const accounts = useFetch(fetchAccounts);
  const usable = (accounts.data ?? []).filter((a) => a.fully_activated);
  const [create, setCreate] = useState(false);
  const [source, setSource] = useState("");
  const [topUp, setTopUp] = useState<VirtualCard | null>(null);
  const [amount, setAmount] = useState("");
  const [remove, setRemove] = useState<VirtualCard | null>(null);
  const [busy, setBusy] = useState(false);

  const act = async (fn: () => Promise<unknown>, ok: string, done: () => void) => {
    setBusy(true);
    try { await fn(); toast.success(ok); done(); void cards.reload(true); void accounts.reload(true); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Something went wrong"); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Virtual cards" description="Up to three disposable cards, funded from your accounts." actions={<Button variant="accent" onClick={() => { setSource(usable[0]?.account_number ?? ""); setCreate(true); }} disabled={!usable.length}><Plus />New card</Button>} />
      {cards.loading ? <div className="grid gap-5 md:grid-cols-2"><Skeleton className="aspect-[1.586/1] rounded-2xl" /></div> : (cards.data ?? []).length === 0 ? (
        <Card className="border-dashed"><CardContent className="p-10 text-center text-sm text-muted-foreground">{usable.length ? "You have no virtual cards yet." : "You need an active account before you can create a card."}</CardContent></Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {(cards.data ?? []).map((c) => (
            <div key={c.id} className="space-y-3">
              <CardFace card={c} />
              <div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">Status: {titleCase(c.status)}</span>
                <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => { setAmount(""); setTopUp(c); }}>Top up</Button><Button size="sm" variant="ghost" className="text-destructive" onClick={() => setRemove(c)}><Trash2 />Delete</Button></div></div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={create} onOpenChange={setCreate}><DialogContent>
        <DialogHeader><DialogTitle>New virtual card</DialogTitle><DialogDescription>The card is linked to the account you choose.</DialogDescription></DialogHeader>
        <Field id="src" label="Linked account"><Select id="src" value={source} onChange={(e) => setSource(e.target.value)}>{usable.map((a) => <option key={a.id} value={a.account_number}>{groupDigits(a.account_number)} · {money(a.account_balance, a.currency)}</option>)}</Select></Field>
        <DialogFooter><Button variant="outline" onClick={() => setCreate(false)}>Cancel</Button><Button loading={busy} onClick={() => void act(() => api.post("/cards/virtual-cards/", { bank_account_number: source }), "Card created", () => setCreate(false))}>Create card</Button></DialogFooter>
      </DialogContent></Dialog>

      <Dialog open={!!topUp} onOpenChange={(o) => !o && setTopUp(null)}><DialogContent>
        <DialogHeader><DialogTitle>Top up card</DialogTitle><DialogDescription>Moves money from the linked account onto the card.</DialogDescription></DialogHeader>
        <Field id="tu" label="Amount"><Input id="tu" type="number" step="0.01" min="0.1" value={amount} onChange={(e) => setAmount(e.target.value)} autoFocus /></Field>
        <DialogFooter><Button variant="outline" onClick={() => setTopUp(null)}>Cancel</Button><Button loading={busy} disabled={Number(amount) < 0.1} onClick={() => void act(() => api.post(`/cards/virtual-cards/${topUp!.id}/top-up/`, { amount: Number(amount).toFixed(2) }), "Card topped up", () => setTopUp(null))}>Top up</Button></DialogFooter>
      </DialogContent></Dialog>

      <Dialog open={!!remove} onOpenChange={(o) => !o && setRemove(null)}><DialogContent>
        <DialogHeader><DialogTitle>Delete this card?</DialogTitle><DialogDescription>This cannot be undone.</DialogDescription></DialogHeader>
        <DialogFooter><Button variant="outline" onClick={() => setRemove(null)}>Cancel</Button><Button variant="destructive" loading={busy} onClick={() => void act(() => api.del(`/cards/virtual-cards/${remove!.id}/`), "Card deleted", () => setRemove(null))}>Delete</Button></DialogFooter>
      </DialogContent></Dialog>
    </>
  );
}
