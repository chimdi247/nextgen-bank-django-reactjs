/**
 * OTP LOGIN CHAIN TEST - the slowest user-visible path of the platform:
 *   POST /auth/login/ -> Django -> RabbitMQ -> Celery worker -> SMTP -> Mailpit -> (k6 polls Mailpit) -> POST /auth/verify-otp/
 * Measures how long the e-mailed code takes to arrive (`otp_delivery_ms`) while the chain is loaded, and that every login succeeds.
 * Argon2 password hashing makes this CPU-heavy on the API; the e-mail leg loads RabbitMQ and the Celery worker.
 * Watch: RabbitMQ ready / unacked / publish-ack rates, Celery task runtime (Flower), api and celeryworker CPU.
 *
 *   tests/run.sh otp          OTP_VUS=10 DURATION=3m tests/run.sh otp
 */
import { sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { int, testId, PASSWORD, PREFIX } from './lib/config.js';
import * as api from './lib/api.js';

const delivery = new Trend('otp_delivery_ms', true);
const failures = new Counter('otp_login_failures');
const USERS = int('USERS', 10);

export const options = {
  scenarios: { otp: { executor: 'constant-vus', vus: Math.min(int('OTP_VUS', 5), USERS), duration: __ENV.DURATION || '2m' } },
  tags: { testid: testId('otp-login') },
  thresholds: { otp_delivery_ms: ['p(95)<8000'], otp_login_failures: ['count==0'], 'http_req_failed': ['rate<0.01'] },
};

export default function () {
  const email = `${PREFIX}${__VU}@example.com`;       // one mailbox per VU: no cross-talk
  const session = api.authenticate(email, PASSWORD, 'login');
  if (!session) { failures.add(1); sleep(1); return; }
  delivery.add(session.otpDelayMs);
  api.ok(api.accounts(session.token), 'accounts after login');
  sleep(1);
}
