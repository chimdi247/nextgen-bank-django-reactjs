/**
 * SMOKE TEST - "is the platform alive and are the main flows and security rules correct?"
 * 2 VUs, 1 minute. Every iteration checks health, auth rules, reads, and the unauthenticated / forbidden paths.
 * Run it after every deploy:  tests/run.sh smoke
 */
import { check, group, sleep } from 'k6';
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';

export const options = {
  scenarios: { smoke: { executor: 'constant-vus', vus: int('VUS', 2), duration: __ENV.DURATION || '1m' } },
  tags: { testid: testId('smoke') },
  setupTimeout: '300s',
  thresholds: { http_req_failed: ['rate<0.01'], checks: ['rate==1'], 'http_req_duration{ep:accounts}': ['p(95)<1000'] },
};

export const setup = () => api.provision(2);

export default function (d) {
  const u = d.users[(__VU - 1) % d.users.length];
  group('platform', () => {
    const h = api.health();
    check(h, { 'health 200': (r) => r.status === 200, 'database ok': (r) => r.json('checks.database') === 'ok' });
    check(api.call('GET', '/schema/', { ep: 'docs' }), { 'OpenAPI schema served': (r) => r.status === 200 });
  });
  group('authentication', () => {
    check(api.call('GET', '/accounts/', { ep: 'unauth', expected: [401, 403] }), { 'no token rejected': (r) => r.status === 401 || r.status === 403 });
    check(api.call('GET', '/accounts/', { token: 'not-a-jwt', ep: 'unauth', expected: [401, 403] }), { 'garbage token rejected': (r) => r.status === 401 || r.status === 403 });
    check(api.call('POST', '/auth/login/', { ep: 'login_bad', expected: [400, 401, 404], body: { email: u.email, password: 'wrong-password' } }), { 'wrong password rejected': (r) => r.status >= 400 && r.status < 500 });
    check(api.call('GET', '/auth/users/me/', { token: u.token, ep: 'me' }), { 'me: role customer, no security answer': (r) => r.json('role') === 'customer' && r.json('security_answer') === undefined });
  });
  group('customer reads', () => {
    const accts = api.data(api.accounts(u.token));
    check(accts, { 'has an active account': (a) => a && a.length > 0 && a[0].fully_activated === true });
    api.ok(api.transactions(u.token), 'transactions');
    api.ok(api.cards(u.token), 'cards');
    api.ok(api.profile(u.token), 'profile');
    const other = d.users[(d.users.indexOf(u) + 1) % d.users.length];
    check(api.lookup(u.token, other.account), { 'lookup masks balance': (r) => r.status === 200 && r.json('account_balance') === undefined });
  });
  group('authorisation', () => {
    check(api.call('GET', '/accounts/stats/', { token: u.token, ep: 'forbidden', expected: [403] }), { 'customer cannot read bank stats (403)': (r) => r.status === 403 });
    check(api.call('GET', '/accounts/pending/', { token: u.token, ep: 'forbidden', expected: [403] }), { 'customer cannot see the KYC queue (403)': (r) => r.status === 403 });
    check(api.call('POST', '/accounts/deposit/', { token: u.token, ep: 'forbidden', expected: [403], body: { account_number: u.account, amount: '1.00' } }), { 'customer cannot deposit (403)': (r) => r.status === 403 });
  });
  sleep(1);
}
