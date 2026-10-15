import { check, sleep } from 'k6';
import { THINK_TIME } from './config.js';
import * as api from './api.js';

export const think = () => { if (THINK_TIME > 0) sleep(THINK_TIME * (0.5 + Math.random())); };

const reauthMs = 20 * 60 * 1000;           // access tokens live 30 min: soak tests renew before that
const sessions = {};                       // per-VU copy of the token (module state is per VU in k6)

function me(d) {
  const u = d.users[(__VU - 1) % d.users.length];
  const s = sessions[u.email] || (sessions[u.email] = { token: u.token, at: u.at });
  if (Date.now() - s.at > reauthMs) {
    const fresh = api.authenticate(u.email, undefined, 'reauth');
    if (fresh) { s.token = fresh.token; s.at = fresh.at; }
  }
  return { ...u, token: s.token };
}

/**
 * Customer mix (reads dominate, like real banking traffic):
 *   45 % balances  - 25 % history - 10 % recipient lookup - 5 % cards - 5 % profile - 3 % health - 2 % unauthenticated (must be 401)
 */
export function customerIteration(d, withThink = true) {
  const u = me(d);
  const r = Math.random();
  if (r < 0.45) check(api.accounts(u.token), { 'accounts: 200 + list': (x) => x.status === 200 && Array.isArray(api.data(x)) });
  else if (r < 0.70) api.ok(api.transactions(u.token), 'transactions');
  else if (r < 0.80) {
    const other = d.users[Math.floor(Math.random() * d.users.length)];
    api.ok(api.lookup(u.token, other.account), 'lookup');
  } else if (r < 0.85) api.ok(api.cards(u.token), 'cards');
  else if (r < 0.90) api.ok(api.profile(u.token), 'profile');
  else if (r < 0.98) api.ok(api.health(), 'health');
  else check(api.call('GET', '/accounts/', { ep: 'unauth', expected: [401, 403] }), { 'no token -> 401/403': (x) => x.status === 401 || x.status === 403 });
  if (withThink) think();
}

export const standardThresholds = (p95 = 800, p99 = 1500) => ({
  http_req_failed: ['rate<0.01'],
  checks: ['rate>0.99'],
  'http_req_duration{ep:accounts}': [`p(95)<${p95}`, `p(99)<${p99}`],
  'http_req_duration{ep:transactions}': [`p(95)<${p95 * 1.5}`],
});
