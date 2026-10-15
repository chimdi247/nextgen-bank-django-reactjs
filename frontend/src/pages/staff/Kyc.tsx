import { useState } from "react";
import { BadgeCheck, ImageOff } from "lucide-react";
import { toast } from "sonner";
import { Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, mediaUrl } from "@/lib/api";
import { formatErr } from "@/lib/errors";
import { CURRENCY, dateTime, groupDigits, titleCase } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Page, PendingAccount } from "@/lib/types";

const SIZE = 10;

function Doc({ label, url }: { label: string; url?: string | null }) {
  const src = mediaUrl(url);
  return (
    <div><p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-md border bg-secondary/40">
        {src ? <img src={src} alt={label} className="h-full w-full object-cover" onError={(e) => ((e.target as HTMLImageElement).style.display = "none")} /> : <ImageOff className="h-6 w-6 text-muted-foreground" />}
      </div></div>
  );
}

export default function Kyc() {
  const [state, setState] = useState("pending");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [target, setTarget] = useState<PendingAccount | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const q = useFetch(() => api.get<Page<PendingAccount>>("/accounts/pending/", { state, search, page: page + 1, page_size: SIZE }), [state, search, page]);
  const pages = Math.max(1, Math.ceil((q.data?.count ?? 0) / SIZE));

  const verify = async () => {
    if (!target) return;
    setBusy(true);
    try {
      await api.patch(`/accounts/verify/${target.id}/`, { kyc_submitted: true, kyc_verified: true, verification_notes: notes || "Identity documents verified" });
      toast.success(`${target.holder_name}: account verified and activated`); setTarget(null); void q.reload(true);
    } catch (e) { toast.error(formatErr(e)); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="KYC verification" description="Review identity documents and activate new accounts." actions={
        <div className="flex gap-2"><div className="w-36"><Select value={state} onChange={(e) => { setState(e.target.value); setPage(0); }} aria-label="State"><option value="pending">Pending</option><option value="verified">Verified</option><option value="all">All</option></Select></div>
          <Input className="w-56" placeholder="Search name, e-mail or number" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} aria-label="Search" /></div>} />
      {q.error && <p className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{q.error}</p>}
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Customer</TableHead><TableHead>Account</TableHead><TableHead>Profile</TableHead><TableHead>Opened</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader>
          <TableBody>
            {q.loading ? [0, 1, 2].map((i) => <TableRow key={i}><TableCell colSpan={5}><Skeleton className="h-8" /></TableCell></TableRow>)
              : (q.data?.results ?? []).length === 0 ? <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Nothing in this queue.</TableCell></TableRow>
              : q.data!.results.map((a) => (
                <TableRow key={a.id}>
                  <TableCell><p className="font-semibold">{a.holder_name}</p><p className="text-xs text-muted-foreground">{a.holder_email}</p></TableCell>
                  <TableCell><span className="tnum font-mono text-xs">{groupDigits(a.account_number)}</span><p className="text-xs text-muted-foreground">{titleCase(a.account_type)} · {CURRENCY[a.currency].code}</p></TableCell>
                  <TableCell>{a.profile_complete ? <Badge variant="success">Complete</Badge> : <Badge variant="warning">Incomplete</Badge>}</TableCell>
                  <TableCell className="text-muted-foreground">{dateTime(a.created_at)}</TableCell>
                  <TableCell className="text-right">{a.kyc_verified ? <StatusBadge status="verified" /> : <Button size="sm" onClick={() => { setNotes(""); setTarget(a); }}>Review</Button>}</TableCell>
                </TableRow>))}
          </TableBody>
        </Table>
        <Pagination page={page} pages={pages} total={q.data?.count ?? 0} onChange={setPage} />
      </Card>

      <Dialog open={!!target} onOpenChange={(o) => !o && setTarget(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{target?.holder_name}</DialogTitle><DialogDescription>{target?.holder_email} · national ID {target?.holder_id_no}</DialogDescription></DialogHeader>
          <div className="grid grid-cols-3 gap-3"><Doc label="Portrait" url={target?.photo_url} /><Doc label="ID document" url={target?.id_photo_url} /><Doc label="Signature" url={target?.signature_photo_url} /></div>
          <Field id="notes" label="Verification notes"><Input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Identity documents verified" /></Field>
          <DialogFooter><Button variant="outline" onClick={() => setTarget(null)}>Cancel</Button><Button loading={busy} onClick={verify}><BadgeCheck />Verify and activate</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
