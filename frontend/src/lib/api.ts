const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
const V1 = `${BASE}/api/v1`;

export class ApiError extends Error {
  status: number;
  traceId?: string;
  constructor(message: string, status: number, traceId?: string) {
    super(message);
    this.status = status;
    this.traceId = traceId;
  }
}

let unauthorizedHandler: (() => void) | null = null;
export const onUnauthorized = (fn: () => void) => { unauthorizedHandler = fn; };

/** Last trace id seen in an `X-Trace-Id` response header (shown on the System page / in error toasts). */
export let lastTraceId = "";

type Params = Record<string, string | number | boolean | undefined | null>;

/**
 * Error bodies come in many shapes:
 *   {"status_code":400,"initiate_transfer":{"error":"Insufficient funds"}}   (GenericJSONRenderer envelope)
 *   {"detail":"..."}   {"error":"..."}   {"email":["user with this email already exists."]}   {"non_field_errors":[...]}
 * Walk the structure and produce one readable sentence.
 */
export function extractMessage(body: unknown, status: number): string {
  const found: string[] = [];
  const visit = (node: unknown, key?: string) => {
    if (typeof node === "string") {
      if (key === "status_code") return;
      found.push(key && !["error", "detail", "message", "errors", "non_field_errors"].includes(key) ? `${label(key)}: ${node}` : node);
    } else if (Array.isArray(node)) node.forEach((n) => visit(n, key));
    else if (node && typeof node === "object") Object.entries(node as Record<string, unknown>).forEach(([k, v]) => visit(v, k));
  };
  visit(body);
  if (found.length) return Array.from(new Set(found)).join(" ");
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to do that.";
  if (status === 404) return "Not found.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status === 503) return "The service is temporarily unavailable.";
  if (status >= 500) return "Something went wrong on our side. Please try again.";
  return "The request could not be completed.";
}
const label = (k: string) => k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

/** GenericJSONRenderer wraps successful payloads as {status_code, <label>: data}. */
export function unwrap<T>(body: unknown): T {
  if (body && typeof body === "object" && !Array.isArray(body) && "status_code" in (body as object)) {
    const rest = Object.entries(body as Record<string, unknown>).filter(([k]) => k !== "status_code");
    if (rest.length === 1) return rest[0][1] as T;
  }
  return body as T;
}

interface Options { params?: Params; body?: unknown; form?: FormData; noRefresh?: boolean }

async function raw(method: string, path: string, { params, body, form }: Options = {}) {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") qs.set(k, String(v)); });
  const headers: Record<string, string> = { Accept: "application/json" };
  let payload: BodyInit | undefined;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  try {
    return await fetch(`${V1}${path}${qs.size ? `?${qs}` : ""}`, { method, headers, body: payload, credentials: "same-origin" });
  } catch {
    throw new ApiError("Cannot reach the server. Check that the platform is running.", 0);
  }
}

let refreshing: Promise<boolean> | null = null;
async function refreshSession(): Promise<boolean> {
  refreshing ??= raw("POST", "/auth/refresh/").then((r) => r.ok).catch(() => false).finally(() => { setTimeout(() => (refreshing = null), 0); });
  return refreshing;
}

async function request<T>(method: string, path: string, opts: Options = {}): Promise<T> {
  let res = await raw(method, path, opts);
  const isAuthCall = /^\/auth\/(login|verify-otp|refresh|users\/(activation|reset_password))/.test(path);
  if (res.status === 401 && !opts.noRefresh && !isAuthCall && (await refreshSession())) res = await raw(method, path, opts);

  const traceId = res.headers.get("X-Trace-Id") ?? undefined;
  if (traceId) lastTraceId = traceId;
  const text = await res.text();
  let json: unknown = null;
  try { json = text ? JSON.parse(text) : null; } catch { /* empty / non-JSON */ }

  if (res.status === 401 && !isAuthCall) {
    unauthorizedHandler?.();
    throw new ApiError(extractMessage(json, 401), 401, traceId);
  }
  if (!res.ok) throw new ApiError(extractMessage(json, res.status), res.status, traceId);
  return unwrap<T>(json);
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path, { params }),
  post: <T>(path: string, body?: unknown, opts: Options = {}) => request<T>("POST", path, { ...opts, body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  patchForm: <T>(path: string, form: FormData) => request<T>("PATCH", path, { form }),
  del: <T>(path: string) => request<T>("DELETE", path),
};

/** Lists may be a bare array or a DRF page. */
export function asList<T>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  if (v && typeof v === "object" && Array.isArray((v as { results?: unknown }).results)) return (v as { results: T[] }).results;
  return [];
}

/** Profile photos are stored with an absolute URL of the public origin; make them same-origin so they load anywhere. */
export function mediaUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  return url.replace(/^https?:\/\/[^/]+(?=\/media\/)/, "");
}
