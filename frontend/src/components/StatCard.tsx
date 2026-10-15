import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function StatCard({ label, value, icon: Icon, hint, loading }: { label: string; value: string | number; icon: LucideIcon; hint?: string; loading?: boolean }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-secondary text-primary"><Icon className="h-4 w-4" /></span>
      </div>
      {loading ? <Skeleton className="mt-3 h-8 w-24" /> : <p className="tnum mt-2 font-display text-3xl font-semibold">{value}</p>}
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}
