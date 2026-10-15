import http from 'k6/http';
import { check, fail } from 'k6';
import { BASE_URL, PASSWORD, PREFIX } from './config.js';
import { clearMailbox, waitForOtp } from './mailpit.js';

/**
 * Thin wrapper around k6/http.  `ep` = short label for thresholds ('http_req_duration{ep:accounts}'),
 * `name` = constant URL name, `expected` = HTTP statuses that are NOT failures (negative tests).
 * The JWT travels as the `access` cookie, exactly like the browser sends it.
 */
export function call(method, path, { body, token, ep, name, expected = [200], params } = {}) {
  const p = {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    tags: { name: name || `${method} ${path}`, ep: ep || 'other' },
    responseCallback: http.expectedStatuses(...expected),
    cookies: token ? { access: token } : {},
  };
  const url = `${BASE_URL}/api/v1${path}${params ? '?' + Object.entries(params).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&') : ''}`;
  if (method === 'GET') return http.get(url, p);
  return http.request(method, url, body === undefined ? null : JSON.stringify(body), p);
}

export const json = (res) => { try { return res.json(); } catch (e) { return null; } };
const unwrap = (b) => (b && b.status_code !== undefined && Object.keys(b).length === 2 ? b[Object.keys(b).find((k) => k !== 'status_code')] : b);
export const data = (res) => unwrap(json(res));

export const health = () => call('GET', '/health/', { ep: 'health' });
export const accounts = (t) => call('GET', '/accounts/', { token: t, ep: 'accounts' });
export const transactions = (t, page = 1) => call('GET', '/accounts/transactions/', { token: t, ep: 'transactions', params: { page } });
export const cards = (t) => call('GET', '/cards/virtual-cards/', { token: t, ep: 'cards' });
export const profile = (t) => call('GET', '/profiles/my-profile/', { token: t, ep: 'profile' });
export const lookup = (t, n) => call('GET', '/accounts/lookup/', { token: t, ep: 'lookup', name: 'GET /accounts/lookup/', params: { account_number: n } });

/**
 * Two-step login: password -> OTP e-mailed through RabbitMQ + Celery + SMTP -> Mailpit -> code -> cookies.
 * Returns { token, refresh, otpDelayMs } or null. `ep` lets setup traffic be excluded from dashboards.
 */
export function authenticate(email, password = PASSWORD, ep = 'setup') {
  clearMailbox(email);
  const t0 = Date.now();
  const r1 = call('POST', '/auth/login/', { ep, body: { email, password }, name: 'POST /auth/login/' });
  if (r1.status !== 200) return null;
  const otp = waitForOtp(email);
  const otpDelayMs = Date.now() - t0;
  if (!otp) return null;
  const r2 = call('POST', '/auth/verify-otp/', { ep, body: { email, otp }, name: 'POST /auth/verify-otp/' });
  if (r2.status !== 200 || !r2.cookies.access) return null;
  return { token: r2.cookies.access[0].value, refresh: r2.cookies.refresh && r2.cookies.refresh[0].value, otpDelayMs, at: Date.now() };
}

/**
 * setup(): authenticate `count` seeded customers (`manage.py seed_demo_data --customers N`, done by tests/run.sh)
 * and read their account numbers. Everything here is tagged ep=setup and excluded from the dashboards.
 */
export function provision(count) {
  const users = [];
  for (let i = 1; i <= count; i++) {
    const email = `${PREFIX}${i}@example.com`;
    const session = authenticate(email);
    if (!session) fail(`could not sign in ${email}. Seed users first:  docker compose -f local.yml exec api python manage.py seed_demo_data --customers ${count} --prefix ${PREFIX}`);
    const accts = data(call('GET', '/accounts/', { token: session.token, ep: 'setup' })) || [];
    if (!accts.length) fail(`${email} has no account: re-run seed_demo_data`);
    users.push({ email, token: session.token, account: accts[0].account_number, at: session.at });
  }
  return { users };
}

export const ok = (res, label, status = 200) => check(res, { [`${label}: ${status}`]: (r) => r.status === status });
