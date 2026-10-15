/**
 * READ-HEAVY TEST - balances, paged history and profile only (no writes, no e-mail).
 * Isolates the request path nginx -> gunicorn -> PgBouncer -> PostgreSQL, plus Redis for throttling counters.
 * Watch: PgBouncer client vs server connections (multiplexing ratio), Postgres cache hit ratio, Redis hit ratio / commands per second.
 *
 *   tests/run.sh read-heavy        READ_VUS=80 tests/run.sh read-heavy
 */
import { check } from 'k6';
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { think } from './lib/journeys.js';

export const options = {
  scenarios: { reads: { executor: 'ramping-vus', stages: [{ duration: '1m', target: int('READ_VUS', 40) }, { duration: __ENV.HOLD || '4m', target: int('READ_VUS', 40) }, { duration: '30s', target: 0 }] } },
  tags: { testid: testId('read-heavy') },
  setupTimeout: '600s',
  thresholds: { http_req_failed: ['rate<0.01'], 'http_req_duration{ep:accounts}': ['p(95)<600'], 'http_req_duration{ep:transactions}': ['p(95)<900'], checks: ['rate>0.99'] },
};

export const setup = () => api.provision(int('USERS', 20));

export default function (d) {
  const u = d.users[(__VU - 1) % d.users.length];
  const r = Math.random();
  if (r < 0.5) check(api.accounts(u.token), { 'accounts 200': (x) => x.status === 200 });
  else if (r < 0.85) check(api.transactions(u.token, 1 + Math.floor(Math.random() * 3)), { 'transactions 200': (x) => x.status === 200 });
  else check(api.profile(u.token), { 'profile 200': (x) => x.status === 200 });
  think();
}
