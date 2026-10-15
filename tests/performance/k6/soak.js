/**
 * SOAK (ENDURANCE) TEST - "does it stay healthy for hours?" Finds memory leaks, connection leaks (PgBouncer / Redis clients),
 * queue creep, DB bloat and disk growth. Constant SOAK_VUS (10) for DURATION (default 1h; use 4h - 8h for a real soak).
 * Tokens are renewed every 20 minutes through the real OTP flow (lib/journeys.js).
 * Watch: container memory %, Redis connected clients, Postgres connections / dead tuples, RabbitMQ backlog, p95 drift.
 *
 *   tests/run.sh soak          DURATION=4h SOAK_VUS=15 tests/run.sh soak
 */
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { customerIteration } from './lib/journeys.js';

export const options = {
  scenarios: {
    soak: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: int('SOAK_VUS', 10) },
        { duration: __ENV.DURATION || '1h', target: int('SOAK_VUS', 10) },
        { duration: '1m', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  tags: { testid: testId('soak') },
  setupTimeout: '600s',
  thresholds: { http_req_failed: ['rate<0.01'], 'http_req_duration{ep:accounts}': ['p(95)<1000'], checks: ['rate>0.99'] },
};

export const setup = () => api.provision(int('USERS', 20));
export default customerIteration;
