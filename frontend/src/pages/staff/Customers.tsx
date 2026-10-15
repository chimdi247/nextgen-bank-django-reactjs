import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { initials } from "@/lib/format";
import { useFetch } from "@/lib/hooks";
import type { Page } from "@/lib/types";

const SIZE = 10;
interface Row { id?: string; full_name?: string; first_name?: string; last_name?: string; email?: string; phone_number?: string; city?: string; country?: string; employment_status?: string }

export default function Customers() {
  const [page, setPage] = useState(0);
  const q = useFetch(() => api.get<Page<Row>>("/profiles/all/", { page: page + 1, page_size: SIZE }), [page]);
  const pages = Math.max(1, Math.ceil((q.data?.count ?? 0) / SIZE));
  return (
    <>
      <PageHeader title="Customers" description="Every customer profile (staff accounts are excluded)." />
      {q.error && <p className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{q.error}</p>}
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Customer</TableHead><TableHead>Phone</TableHead><TableHead>Location</TableHead><TableHead>Employment</TableHead></TableRow></TableHeader>
          <TableBody>
            {q.loading ? [0, 1, 2, 3].map((i) => <TableRow key={i}><TableCell colSpan={4}><Skeleton className="h-8" /></TableCell></TableRow>)
              : (q.data?.results ?? []).map((r, i) => {
                const name = r.full_name ?? `${r.first_name ?? ""} ${r.last_name ?? ""}`.trim();
                return (
                  <TableRow key={r.id ?? i}>
                    <TableCell><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-primary">{initials(name)}</span><div><p className="font-semibold">{name}</p><p className="text-xs text-muted-foreground">{r.email}</p></div></div></TableCell>
                    <TableCell className="tnum">{r.phone_number}</TableCell>
                    <TableCell>{[r.city, r.country].filter(Boolean).join(", ")}</TableCell>
                    <TableCell className="capitalize">{(r.employment_status ?? "").replace(/_/g, " ")}</TableCell>
                  </TableRow>);
              })}
          </TableBody>
        </Table>
        <Pagination page={page} pages={pages} total={q.data?.count ?? 0} onChange={setPage} />
      </Card>
    </>
  );
}
