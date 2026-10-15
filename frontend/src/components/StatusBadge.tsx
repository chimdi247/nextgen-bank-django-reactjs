import { Badge } from "@/components/ui/badge";
import { titleCase } from "@/lib/format";

export function StatusBadge({ status }: { status: string }) {
  const v = ["active", "completed", "verified", "success"].includes(status) ? "success"
    : ["pending", "inactive", "submitted"].includes(status) ? "warning"
    : "destructive";
  return <Badge variant={v}>{titleCase(status)}</Badge>;
}
