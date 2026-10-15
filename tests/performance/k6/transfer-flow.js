/**
 * TRANSFER FLOW + MONEY-CONSERVATION TEST
 * Runs the real three-step transfer (initiate -> security answer -> e-mailed OTP) from many customers at once,
 * all sending to each other: this exercises row locking (select_for_update), PgBouncer transaction pooling,
 * sessions, the RabbitMQ e-mail chain and Redis throttling together.
 * Invariant checked in teardown(): transfers are zero-sum, so the sum of all balances must be unchanged.
 *
 *   tests/run.sh transfers        TRANSFER_VUS=8 DURATION=3m tests/run.sh transfers
 */
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { clearMailbox, waitForOtp } from './lib/mailpit.js';

const USERS = int('USERS', 10);
const done = new Counter('transfers_completed');
const refused = new Counter('transfers_refused');
const total = new Trend('transfer_total_ms', true);

export const options = {
  scenarios: { transfers: { executor: 'constant-vus', vus: Math.min(int('TRANSFER_VUS', 5), USERS), duration: __ENV.DURATION || '2m' } },
  tags: { testid: testId('transfers') },
  setupTimeout: '600s',
  thresholds: { transfer_total_ms: ['p(95)<10000'], http_req_failed: ['rate<0.02'], checks: ['rate>0.99'] },
};

const sum = (d) => d.users.reduce((s, u) => s + (api.data(api.call('GET', '/accounts/', { token: u.token, ep: 'setup' })) || []).reduce((t, a) => t + Number(a.account_balance), 0), 0);

export function setup() {
  const d = api.provision(USERS);
  d.initialTotal = sum(d);
  return d;
}

export default function (d) {
  const i = (__VU - 1) % d.users.length;
  const from = d.users[i];
  const to = d.users[(i + 1 + Math.floor(Math.random() * (d.users.length - 1))) % d.users.length];
  const t0 = Date.now();

  const a = api.call('POST', '/accounts/transfer/initiate/', { token: from.token, ep: 'transfer_initiate', body: { sender_account: from.account, receiver_account: to.account, amount: '1.00', description: 'k6 transfer' } });
  if (!check(a, { 'initiate 200': (r) => r.status === 200 })) { refused.add(1); sleep(1); return; }

  const b = api.call('POST', '/accounts/transfer/verify-security-question/', { token: from.token, ep: 'transfer_question', body: { security_answer: 'blue' } });
  check(b, { 'security answer accepted': (r) => r.status === 200 });
  const otp = waitForOtp(from.email);
  if (!otp) { refused.add(1); return; }

  const c = api.call('POST', '/accounts/transfer/verify-otp/', { token: from.token, ep: 'transfer_confirm', body: { otp } });
  if (check(c, { 'transfer completed (201)': (r) => r.status === 201 })) { done.add(1); total.add(Date.now() - t0); } else refused.add(1);
  clearMailbox(from.email);
  sleep(0.5);
}

export function teardown(d) {
  const now = sum(d);
  console.log(`total money before ${d.initialTotal.toFixed(2)} / after ${now.toFixed(2)}`);
  check(now, { 'money is conserved (sum of balances unchanged)': (n) => Math.abs(n - d.initialTotal) < 0.005 });
}
