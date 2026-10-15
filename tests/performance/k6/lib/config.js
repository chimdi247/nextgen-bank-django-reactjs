// Shared configuration. Override any value with `-e NAME=value` (k6) or an environment variable (tests/run.sh).
export const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8080').replace(/\/$/, '');
export const MAILPIT_URL = (__ENV.MAILPIT_URL || 'http://localhost:8025').replace(/\/$/, '');
export const PROM_URL = (__ENV.PROM_URL || 'http://prometheus:9090').replace(/\/$/, '');
export const PASSWORD = 'Perf#12345';                         // password of the customers created by `manage.py seed_demo_data`
export const PREFIX = __ENV.PREFIX || 'perf';                 // perf1@example.com ... perf<N>@example.com
export const THINK_TIME = parseFloat(__ENV.THINK_TIME || '1'); // average seconds between user actions

export const int = (name, fallback) => parseInt(__ENV[name] || String(fallback), 10);

/** Tag on every metric of a run: tests/run.sh passes TEST_ID=<timestamp> so each run is its own series in Grafana. */
export const testId = (name) => (__ENV.TEST_ID ? `${name}-${__ENV.TEST_ID}` : name);
