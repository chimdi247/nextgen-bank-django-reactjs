import type { ReactNode } from "react";
import { ShieldCheck, Zap, MailCheck } from "lucide-react";
import { BrandMark } from "@/components/Brand";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="card-sheen relative hidden flex-col justify-between overflow-hidden bg-primary p-12 text-primary-foreground lg:flex">
        <div className="relative flex items-center gap-3"><BrandMark className="h-10 w-10" /><span className="font-display text-2xl font-semibold tracking-tight">NextGen Bank</span></div>
        <div className="relative max-w-lg">
          <h2 className="font-display text-5xl font-semibold leading-[1.06] tracking-tight">Banking that moves at the speed of you.</h2>
          <p className="mt-5 text-lg text-white/70">Open an account, send money and manage virtual cards, protected by two-step sign-in and a security question on every payment.</p>
          <ul className="mt-10 space-y-4 text-sm text-white/80">
            <li className="flex items-center gap-3"><Zap className="h-5 w-5 text-accent" />Transfers settle in seconds</li>
            <li className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-accent" />One-time codes by e-mail at sign-in and on every transfer</li>
            <li className="flex items-center gap-3"><MailCheck className="h-5 w-5 text-accent" />A receipt in your inbox for every movement</li>
          </ul>
        </div>
        <p className="relative text-sm text-white/45">Django · Celery · PostgreSQL · Redis · RabbitMQ, observed end to end.</p>
      </div>
      <div className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden"><BrandMark className="h-8 w-8" /><span className="font-display text-xl font-semibold">NextGen Bank</span></div>
          <h1 className="text-3xl font-semibold">{title}</h1>
          <p className="mb-7 mt-2 text-sm text-muted-foreground">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
