#!/usr/bin/env bash
# Runs a k6 test inside the docker compose network and streams its metrics to Prometheus,
# so the run can be watched live in Grafana:  http://localhost:3001/d/nb-k6
#
#   tests/performance/run.sh <test> [extra k6 args]
#
#   smoke        1 min, 2 VUs: health, auth rules, reads, 401/403 negatives          (CI gate)
#   load         ~8 min, ramp to LOAD_VUS (20)                                         (SLO check)
#   stress       ~20 min, steps up to PEAK_VUS (120), then recovery
#   spike        ~6 min, 5 -> 150 -> 5 VUs
#   soak         1 h (DURATION=4h ...), constant SOAK_VUS (10)
#   breakpoint   ~15 min, rising arrival rate until the SLOs break (self-aborting)
#   otp          2 min: login OTP chain  API -> RabbitMQ -> Celery -> SMTP -> Mailpit
#   transfers    2 min: real 3-step transfers + money-conservation check
#   read-heavy   ~6 min: balances / history / profile only
#   suite        smoke -> load -> spike -> transfers (stops at the first failure)

# LOAD_VUS=50 HOLD=10m make test-load
# PEAK_VUS=60 make test-stress
# DURATION=30m SOAK_VUS=20 make test-soak
# VUS=5 DURATION=2m make test-smoke

# PEAK_VUS=60 make test-stress      # a gentler first try
# PEAK_VUS=250 make test-stress     # heavier, once 120 looks comfortable
#
# Customers perf1..perf<USERS> are created (idempotently) with `manage.py seed_demo_data` before every run.
# Tune with env vars, e.g.   LOAD_VUS=50 HOLD=10m tests/performance/run.sh load
set -euo pipefail
cd "$(dirname "$0")/../.."

declare -A FILE=(
  [smoke]=smoke.js [load]=load.js [stress]=stress.js [spike]=spike.js [soak]=soak.js [breakpoint]=breakpoint.js
  [otp]=otp-login.js [transfers]=transfer-flow.js [read-heavy]=read-heavy.js
)
declare -A USERS_DEFAULT=([smoke]=2 [load]=20 [stress]=40 [spike]=40 [soak]=20 [breakpoint]=50 [otp]=10 [transfers]=10 [read-heavy]=20)
FORWARD=(USERS VUS LOAD_VUS PEAK_VUS BASE_VUS SPIKE_VUS SOAK_VUS READ_VUS OTP_VUS TRANSFER_VUS DURATION HOLD RAMP RAMP_UP RAMP_DOWN
         MAX_RATE MAX_VUS THINK_TIME BASE_URL MAILPIT_URL PROM_URL PREFIX)
COMPOSE=(docker compose -f local.yml)

run_one() {
  local name="$1"; shift
  local file="${FILE[$name]:-}"
  [[ -n "$file" ]] || { echo "unknown test '$name'. Choose: ${!FILE[*]} suite" >&2; exit 2; }

  local users="${USERS:-${USERS_DEFAULT[$name]}}"
  echo "==> seeding $users verified, funded customers (perf1..perf$users)"
  "${COMPOSE[@]}" exec -T api python manage.py seed_demo_data --customers "$users" --prefix perf >/dev/null

  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local args=(--profile tests run --rm -e "TEST_ID=$ts" -e "USERS=$users")
  for v in "${FORWARD[@]}"; do [[ "$v" != USERS && -n "${!v:-}" ]] && args+=(-e "$v=${!v}"); done

  echo "==> k6 $name  (run id: ${name}-${ts})   live: http://localhost:3001/d/nb-k6"
  "${COMPOSE[@]}" "${args[@]}" k6 run --summary-export "/results/${name}-${ts}.json" "/scripts/${file}" "$@"
}

[[ $# -ge 1 ]] || { sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
test_name="$1"; shift
if [[ "$test_name" == "suite" ]]; then for t in smoke load spike transfers; do run_one "$t" "$@"; done
else run_one "$test_name" "$@"; fi
