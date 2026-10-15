/**
 * SPIKE TEST - "what happens when traffic suddenly multiplies and then disappears?"
 * BASE_VUS (5) -> SPIKE_VUS (150) in 20 s -> hold 1 min -> back to baseline -> 3 min recovery.
 * Watch: error rate during the spike, PgBouncer queueing, Redis throttle keys, and whether latency recovers.
 *
 *   tests/run.sh spike         SPIKE_VUS=300 tests/run.sh spike
 */
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { customerIteration } from './lib/journeys.js';
const BASE = int('BASE_VUS', 5);
const SPIKE = int('SPIKE_VUS', 150);
export const options = {
  scenarios: {
    spike: {
      executor: 'ramping-vus',
      startVUs: BASE,
      stages: [
        { duration: '1m', target: BASE },
        { duration: '20s', target: SPIKE },
        { duration: '1m', target: SPIKE },
        { duration: '20s', target: BASE },
        { duration: '3m', target: BASE },
        { duration: '20s', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  tags: { testid: testId('spike') },
  setupTimeout: '600s',
  thresholds: { http_req_failed: ['rate<0.05'], 'http_req_duration{ep:accounts}': ['p(95)<4000'] },
};

export const setup = () => api.provision(int('USERS', 40));
export default customerIteration;
