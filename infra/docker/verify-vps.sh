#!/usr/bin/env bash
# Smart Catering — VPS Production Verification Script (OPS-02 / Issue #24)
# Runs on the target Linux VPS from the repository root after `docker compose up -d`.
# Never prints secrets or .env values.

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/compose.vps.yaml}"
PROFILES="${COMPOSE_PROFILES_ARGS:---profile proxy}"
HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-90}"
SKIP_RESTART_TEST="${SKIP_RESTART_TEST:-false}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found. Copy .env.example to .env and populate production values first." >&2
  exit 1
fi

read_env_value() {
  local key="$1"
  grep -E "^${key}=" "${ENV_FILE}" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r' || true
}

API_DOMAIN="$(read_env_value API_DOMAIN)"
POSTGRES_USER="$(read_env_value POSTGRES_USER)"
POSTGRES_USER="${POSTGRES_USER:-smartcatering}"
POSTGRES_DB="$(read_env_value POSTGRES_DB)"
POSTGRES_DB="${POSTGRES_DB:-smart_catering}"

# shellcheck disable=SC2206
COMPOSE_CMD=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ${PROFILES})

echo "[1/5] Validating resolved Docker Compose configuration..."
"${COMPOSE_CMD[@]}" config --quiet
echo "  OK: Compose configuration is valid."

echo "[2/5] Waiting for all active containers to report healthy (timeout: ${HEALTH_WAIT_SECONDS}s)..."
deadline=$((SECONDS + HEALTH_WAIT_SECONDS))
while true; do
  unhealthy=0
  running_count=0
  while IFS= read -r cid; do
    [[ -z "${cid}" ]] && continue
    running_count=$((running_count + 1))
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}")"
    if [[ "${status}" != "healthy" ]]; then
      unhealthy=$((unhealthy + 1))
    fi
  done < <("${COMPOSE_CMD[@]}" ps -q)

  if [[ "${running_count}" -gt 0 && "${unhealthy}" -eq 0 ]]; then
    echo "  OK: All ${running_count} active containers are healthy."
    break
  fi
  if [[ "${SECONDS}" -ge "${deadline}" ]]; then
    echo "ERROR: Timed out waiting for healthy containers:" >&2
    "${COMPOSE_CMD[@]}" ps >&2
    exit 1
  fi
  sleep 3
done

echo "[3/5] Verifying internal service port isolation (5432, 8000, 8001, 3002, 3000 must not listen on 0.0.0.0)..."
if command -v ss >/dev/null 2>&1; then
  exposed="$(ss -H -tlnp 2>/dev/null | awk '{print $4}' | grep -E '(0\.0\.0\.0|\*|\[::\]):(5432|8000|8001|3002|3000)$' || true)"
  if [[ -n "${exposed}" ]]; then
    echo "ERROR: Internal port(s) exposed on public interface:" >&2
    echo "${exposed}" >&2
    exit 1
  fi
  echo "  OK: No internal ports exposed on public interfaces."
else
  echo "  WARN: 'ss' not installed; skipping host socket check."
fi

echo "[4/5] Verifying loopback API health and HTTPS TLS endpoint..."
curl --fail --silent --show-error http://127.0.0.1:3001/health >/dev/null
echo "  OK: Loopback API http://127.0.0.1:3001/health returned 200."

if [[ -n "${API_DOMAIN}" ]]; then
  curl --fail --silent --show-error --proto '=https' --tlsv1.2 "https://${API_DOMAIN}/api/v1/health" >/dev/null
  echo "  OK: HTTPS https://${API_DOMAIN}/api/v1/health returned 200 with valid TLS."
  trace_status="$(curl --silent --output /dev/null --write-out '%{http_code}' -X TRACE "https://${API_DOMAIN}/api/v1/health" || true)"
  if [[ "${trace_status}" != "405" ]]; then
    echo "ERROR: Expected HTTP 405 for TRACE on HTTPS proxy, got ${trace_status}." >&2
    exit 1
  fi
  echo "  OK: TRACE method rejected at proxy edge with HTTP 405."
else
  echo "  SKIP: API_DOMAIN not set in ${ENV_FILE}; skipping external HTTPS probe."
fi

if [[ "${SKIP_RESTART_TEST}" == "true" ]]; then
  echo "[5/5] Skipping container restart persistence check (SKIP_RESTART_TEST=true)."
  exit 0
fi

echo "[5/5] Verifying PostgreSQL & ChromaDB persistence across container restart..."
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
  "CREATE TABLE IF NOT EXISTS _ops02_persistence_probe (id INT PRIMARY KEY, checked_at TIMESTAMPTZ DEFAULT NOW()); INSERT INTO _ops02_persistence_probe (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET checked_at = NOW();" >/dev/null

"${COMPOSE_CMD[@]}" restart postgres chroma >/dev/null
sleep 6

row_count="$("${COMPOSE_CMD[@]}" exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT COUNT(*) FROM _ops02_persistence_probe WHERE id = 1;" | tr -d '[:space:]')"
if [[ "${row_count}" != "1" ]]; then
  echo "ERROR: PostgreSQL persistence probe row missing after restart." >&2
  exit 1
fi
"${COMPOSE_CMD[@]}" exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "DROP TABLE IF EXISTS _ops02_persistence_probe;" >/dev/null

"${COMPOSE_CMD[@]}" exec -T ai-service python -c "import sys, urllib.request; r = urllib.request.urlopen('http://chroma:8000/api/v2/heartbeat', timeout=5); sys.exit(0 if r.status == 200 else 1)"
echo "  OK: PostgreSQL data and ChromaDB heartbeat verified persistent across container restarts."
echo "VPS verification PASSED."
