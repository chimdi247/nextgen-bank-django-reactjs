/**
 * BREAKPOINT (CAPACITY) TEST - "what is the maximum throughput before the SLOs break?"
 * Open model: arrival rate climbs from 5 to MAX_RATE iterations/s (default 250) over RAMP (15 min) regardless of how slowly
 * the platform answers. Aborts itself when p95 > 2 s or errors > 5 %; the rate at that moment is your capacity.
 *
 *   tests/run.sh breakpoint    MAX_RATE=500 RAMP=20m tests/run.sh breakpoint
 */
import { int, testId } from './lib/config.js';
import * as api from './lib/api.js';
import { customerIteration } from './lib/journeys.js';

export const options = {
  scenarios: {
    breakpoint: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: int('MAX_VUS', 1500),
      stages: [{ duration: __ENV.RAMP || '15m', target: int('MAX_RATE', 250) }],
    },
  },
  tags: { testid: testId('breakpoint') },
  setupTimeout: '600s',
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '1m' }],
    'http_req_duration{ep:accounts}': [{ threshold: 'p(95)<2000', abortOnFail: true, delayAbortEval: '1m' }],
  },
};

export const setup = () => api.provision(int('USERS', 50));
// open model: the arrival rate is the pacing, so no think time inside the iteration
export default (d) => customerIteration(d, false);
