import { Activity, BarChart3, Database, ExternalLink, FileJson, Gauge, HardDrive, Inbox, ListTree, MessagesSquare, Server } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { lastTraceId } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

const env = import.meta.env as Record<string, string | undefined>;
const grafana = env.VITE_GRAFANA_URL || "http://localhost:3001";
const tools = [
  { name: "Platform overview", desc: "Uptime, SLI / SLO, latency, errors, business KPIs, container & node CPU / memory, logs and traces.", href: `${grafana}/d/nb-overview`, icon: BarChart3 },
  { name: "PostgreSQL", desc: "Replication lag, TPS, % of max connections, active connections.", href: `${grafana}/d/nb-postgres`, icon: Database },
  { name: "PgBouncer", desc: "Client / server connections, waiting clients, pool in use.", href: `${grafana}/d/nb-pgbouncer`, icon: Server },
  { name: "Redis", desc: "Connected clients, cache hit ratio, command throughput, memory used.", href: `${grafana}/d/nb-redis`, icon: HardDrive },
  { name: "RabbitMQ & Celery", desc: "Queue depth, publish / ack rates, unacked messages, task runtimes.", href: `${grafana}/d/nb-rabbitmq`, icon: MessagesSquare },
  { name: "Load-test results (k6)", desc: "Smoke, load, stress, spike and soak runs next to server-side metrics.", href: `${grafana}/d/nb-k6`, icon: Gauge },
  { name: "Alert rules", desc: "CPU and memory above 40 %, plus Postgres, PgBouncer, Redis and RabbitMQ health.", href: `${grafana}/alerting/list`, icon: Activity },
  { name: "Mailpit", desc: "Every e-mail sent: login codes, activation links, receipts, Grafana alerts.", href: env.VITE_MAILPIT_URL || "http://localhost:8025", icon: Inbox },
  { name: "RabbitMQ management", desc: "Exchanges, queues and consumers (rabbit / rabbit_local_password).", href: env.VITE_RABBITMQ_URL || "http://localhost:15672", icon: MessagesSquare },
  { name: "Flower", desc: "Celery workers and task history (flower / flower).", href: env.VITE_FLOWER_URL || "http://localhost:5555", icon: ListTree },
  { name: "RedisInsight", desc: "Browse the cache and throttling keys.", href: env.VITE_REDIS_UI_URL || "http://localhost:5540", icon: HardDrive },
  { name: "API documentation", desc: "OpenAPI / Swagger of the Django API.", href: "/api/v1/docs/", icon: FileJson },
];

export default function System() {
  const health = useFetch(async () => (await fetch("/api/v1/health/")).json() as Promise<{ status: string; checks: Record<string, string> }>);
  const ok = health.data?.status === "ok";
  return (
    <>
      <PageHeader title="System" description="Operational tools for the platform." actions={<Badge variant={health.loading ? "secondary" : ok ? "success" : "destructive"}>API {health.loading ? "checking…" : ok ? "healthy" : "unavailable"}</Badge>} />
      {health.data && <p className="mb-4 text-xs text-muted-foreground">Checks: {Object.entries(health.data.checks).map(([k, v]) => `${k} ${v}`).join(" · ")}{lastTraceId && <> · last trace id <span className="font-mono">{lastTraceId}</span> (paste it into Grafana → Explore → Tempo)</>}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {tools.map(({ name, desc, href, icon: Icon }) => (
          <a key={name} href={href} target="_blank" rel="noreferrer" className="group">
            <Card className="flex h-full items-start gap-4 p-5 transition-colors group-hover:border-accent">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-accent"><Icon className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1"><p className="flex items-center gap-2 font-semibold">{name}<ExternalLink className="h-3.5 w-3.5 text-muted-foreground" /></p><p className="mt-1 text-sm text-muted-foreground">{desc}</p></div>
            </Card>
          </a>
        ))}
      </div>
    </>
  );
}
