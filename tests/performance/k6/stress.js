/**
 * STRESS TEST - "how does the platform behave beyond normal load, and does it recover?"
 * Five plateaus up to PEAK_VUS (default 120) then 0. Thresholds are loose on purpose: read the graphs, not the verdict.
 * Watch: PgBouncer clients waiting, Postgres connections, Redis hit ratio, gunicorn CPU (alerts fire above 40 %).
 *
 *   tests/run.sh stress        PEAK_VUS=250 tests/run.sh stress
 */
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { customerIteration } from './lib/journeys.js';
const PEAK = int('PEAK_VUS', 120);
const step = (f) => Math.max(1, Math.round(PEAK * f));
export const options = {
  scenarios: {
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: step(0.1) }, { duration: '2m', target: step(0.1) },
        { duration: '1m', target: step(0.25) }, { duration: '2m', target: step(0.25) },
        { duration: '1m', target: step(0.5) }, { duration: '2m', target: step(0.5) },
        { duration: '1m', target: step(0.75) }, { duration: '2m', target: step(0.75) },
        { duration: '1m', target: PEAK }, { duration: '3m', target: PEAK },
        { duration: '2m', target: 0 },
      ],
      gracefulRampDown: '1m',
    },
  },
  tags: { testid: testId('stress') },
  setupTimeout: '600s',
  thresholds: { http_req_failed: ['rate<0.10'], 'http_req_duration{ep:accounts}': ['p(95)<3000'] },
};

export const setup = () => api.provision(int('USERS', 40));
export default customerIteration;
