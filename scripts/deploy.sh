#!/usr/bin/env bash
#
# Deploy MealMCP on this host.
#
#   ./scripts/deploy.sh [git-ref]        # git-ref defaults to origin/main
#
# What it does:
#   1. fetch + fast-forward the local branch to the target ref
#   2. re-exec itself from the new checkout
#   3. uv sync
#   4. load the service env, check DB connectivity, apply schema (idempotent)
#   5. restart the systemd service and wait for /healthz
#   6. roll back to the previous commit on any failure
#
# Assumptions:
#   * this checkout is the WorkingDirectory of the systemd unit
#   * service config/secrets live in an EnvironmentFile, also referenced by
#     the unit via `EnvironmentFile=` (default: /etc/meals-app.env)
#   * the deploy user can run `sudo systemctl {restart,is-active} <service>`
#     without a password, e.g. in /etc/sudoers.d/meals-app:
#         brj ALL=(root) NOPASSWD: /usr/bin/systemctl restart meals-app.service, \
#                                  /usr/bin/systemctl is-active meals-app.service
#
set -euo pipefail

REF="${1:-origin/main}"
SERVICE="${MEALS_SERVICE:-meals-app.service}"
ENV_FILE="${MEALS_ENV_FILE:-/etc/meals-app.env}"
HEALTH_URL="${MEALS_HEALTH_URL:-http://127.0.0.1:5000/healthz}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_DIR"

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
die()  { printf '\n\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v uv   >/dev/null || die "uv not found in PATH"
command -v curl >/dev/null || die "curl not found in PATH"
[ -f "$ENV_FILE" ] || die "env file not found: $ENV_FILE"

# --------------------------------------------------------------------------
# Stage 1 - update the working tree, then re-exec from the new script version.
# --------------------------------------------------------------------------
if [ -z "${_MEALS_DEPLOY_REEXEC:-}" ]; then
    if [ -n "$(git status --porcelain)" ] && [ -z "${ALLOW_DIRTY:-}" ]; then
        die "working tree is dirty; commit/stash or re-run with ALLOW_DIRTY=1"
    fi

    log "Fetching origin"
    git fetch --prune --quiet origin

    PREV_SHA="$(git rev-parse HEAD)"
    NEW_SHA="$(git rev-parse "$REF")"

    if [ "$PREV_SHA" = "$NEW_SHA" ]; then
        log "Already at ${NEW_SHA:0:12} - nothing to deploy."
        exit 0
    fi

    log "Deploying ${PREV_SHA:0:12} -> ${NEW_SHA:0:12}"
    git checkout --quiet -B main
    git reset --hard --quiet "$REF"

    export _MEALS_DEPLOY_REEXEC=1
    export _MEALS_DEPLOY_PREV_SHA="$PREV_SHA"
    exec "$REPO_DIR/scripts/deploy.sh" "$REF"
fi

PREV_SHA="$_MEALS_DEPLOY_PREV_SHA"
NEW_SHA="$(git rev-parse HEAD)"

rollback() {
    printf '\n\033[1;31m==> deploy failed - rolling back to %s\033[0m\n' "${PREV_SHA:0:12}" >&2
    git reset --hard --quiet "$PREV_SHA" || true
    uv sync --quiet || true
    sudo systemctl restart "$SERVICE" || true
    exit 1
}
trap rollback ERR

# --------------------------------------------------------------------------
# Stage 2 - dependencies
# --------------------------------------------------------------------------
log "Syncing dependencies"
uv sync --quiet

# --------------------------------------------------------------------------
# Stage 3 - DB connectivity + schema, using the service's own environment
# --------------------------------------------------------------------------
log "Checking database and applying schema"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

uv run python - <<'PY'
import sys
from config import get_pantry_backend, get_pantry_database_url
from db import get_database, close_all_databases
from db_setup_shared import setup_shared_database

backend = get_pantry_backend()
if backend == "postgresql":
    url = get_pantry_database_url()
    if not url:
        sys.exit("PANTRY_DATABASE_URL is not set")
    with get_database("postgresql", url).connection() as conn:
        conn.cursor().execute("SELECT 1")
    if not setup_shared_database(url):
        sys.exit("setup_shared_database() returned failure")
    close_all_databases()
print(f"database OK ({backend})")
PY

# --------------------------------------------------------------------------
# Stage 4 - restart + health check
# --------------------------------------------------------------------------
log "Restarting $SERVICE"
sudo systemctl restart "$SERVICE"

log "Waiting for $HEALTH_URL"
code=""
for _ in $(seq 1 20); do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH_URL" || true)"
    [ "$code" = "200" ] && break
    sleep 1
done
[ "$code" = "200" ] || die "health check failed (last HTTP status: ${code:-none})"
sudo systemctl is-active --quiet "$SERVICE" || die "$SERVICE is not active after restart"

trap - ERR
log "Deployed ${NEW_SHA:0:12}  ✔"
git --no-pager log --oneline "$PREV_SHA..$NEW_SHA" | sed 's/^/    /'
