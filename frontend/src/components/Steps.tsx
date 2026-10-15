import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

/** Horizontal step indicator for the multi-step money flows. */
export function Steps({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="mb-6 flex items-center gap-2" aria-label="Progress">
      {steps.map((s, i) => (
        <li key={s} className="flex flex-1 items-center gap-2">
          <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
            i < current ? "bg-success text-success-foreground" : i === current ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground")}>
            {i < current ? <Check className="h-4 w-4" /> : i + 1}
          </span>
          <span className={cn("hidden text-xs font-semibold sm:block", i === current ? "text-foreground" : "text-muted-foreground")}>{s}</span>
          {i < steps.length - 1 && <span className="h-px flex-1 bg-border" />}
        </li>
      ))}
    </ol>
  );
}
