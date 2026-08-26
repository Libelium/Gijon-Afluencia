#!/usr/bin/env bash
#
# Deploy the platform onto a prepared cluster.
#
# A thin wrapper over the charts in deploy/ — it runs the generator and the helm
# installs in the documented order and stops where a human is required. Run
# deploy/k3s-bootstrap.sh first (or prepare the cluster by hand per
# deploy/docs/02-prerequisites.md).
#
#   deploy/k3s-deploy.sh --env demo --domain pid.gijon.example --registry reg.example.com/pid-gijon
#   deploy/k3s-deploy.sh --env demo --phase core
#   deploy/k3s-deploy.sh --env demo --phase webback
#
# Phases, in order:
#   config    write environments/<env>/config.env and render the values files
#   data      StackGres, MongoDB, RabbitMQ, MinIO
#   core      pid-gijon-core with web-back disabled
#   webback   enable web-back (after the Keycloak post-install step)
#   all       config -> data -> core, then stop at the manual step
#
# The stop between `core` and `webback` is not laziness: the Keycloak realm has
# to exist before web-back can be configured, and copying the realm public key
# and the laravel-backend client secret out of it is a manual step documented in
# deploy/docs/06-post-install.md.
#
# NOT VERIFIED AGAINST A REAL CLUSTER.

set -euo pipefail

K8S="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_NAME=""; DOMAIN=""; REGISTRY=""; PHASE="all"; STORAGE="local"

log()  { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)      ENV_NAME="$2"; shift ;;
    --domain)   DOMAIN="$2"; shift ;;
    --registry) REGISTRY="$2"; shift ;;
    --phase)    PHASE="$2"; shift ;;
    --storage)  STORAGE="$2"; shift ;;
    -h|--help)  sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[[ -n "$ENV_NAME" ]] || die "--env is required"
[[ -d "$K8S/charts" ]] || die "$K8S/charts is missing — run this from a full checkout"
command -v helm    >/dev/null || die "helm not found"
command -v kubectl >/dev/null || die "kubectl not found"
kubectl get nodes >/dev/null 2>&1 || die "no reachable cluster; check KUBECONFIG"

ENV_DIR="$K8S/environments/$ENV_NAME"
CONFIG="$ENV_DIR/config.env"

# ------------------------------------------------------------- config ---
phase_config() {
  log "Scaffolding environments/$ENV_NAME"
  ( cd "$K8S" && ./scripts/generate-env.sh "$ENV_NAME" >/dev/null 2>&1 || true )
  [[ -f "$CONFIG" ]] || die "the generator did not create $CONFIG"

  # Seed the values we were given. Everything else keeps the generator's
  # defaults, which the operator can edit before re-rendering.
  # config.env carries inline comments documenting each key; keep them.
  set_kv() {
    local k="$1" v="$2"
    if grep -qE "^#?${k}=" "$CONFIG"; then
      sed -i -E "s|^#?(${k}=)[^#]*(#.*)?\$|\1${v}    \2|" "$CONFIG"
    else
      printf '%s=%s\n' "$k" "$v" >> "$CONFIG"
    fi
  }
  if [[ -n "$DOMAIN" ]]; then
    set_kv BASE_DOMAIN "$DOMAIN"
    # Explicit, one label deep. Left blank the generator would derive
    # <service>.<PROJECT_NAME>.<BASE_DOMAIN>, which the *.<domain> wildcard
    # certificate k3s-bootstrap.sh creates does not cover (wildcards match a
    # single label) and which is not the DNS that script tells you to point.
    set_kv DOMAIN_API      "api.$DOMAIN"
    set_kv DOMAIN_KEYCLOAK "kc.$DOMAIN"
    set_kv DOMAIN_FRONTEND "app.$DOMAIN"
    set_kv DOMAIN_FIWARE   "fiware.$DOMAIN"
  fi
  [[ -n "$REGISTRY" ]] && set_kv IMAGE_REGISTRY "$REGISTRY"
  set_kv PROJECT_NAME "$ENV_NAME"
  set_kv STORAGE_TYPE "$STORAGE"

  log "Rendering the values files"
  ( cd "$K8S" && ./scripts/generate-env.sh "$ENV_NAME" )

  warn "Review $CONFIG before going further — especially the image tags."
  warn "Secrets are in $ENV_DIR/SECRETS.env (git-ignored). Store them somewhere safe."
}

# --------------------------------------------------------------- data ---
phase_data() {
  log "PostgreSQL / TimescaleDB (StackGres)"
  helm upgrade --install stackgres "$K8S/charts/stackgres" -n postgres --create-namespace \
    -f "$ENV_DIR/stackgres.values.yaml" --wait --timeout 15m

  log "MongoDB"
  helm upgrade --install mongodb "$K8S/charts/mongodb" -n mongodb --create-namespace \
    -f "$ENV_DIR/mongodb.values.yaml" --wait --timeout 15m

  log "RabbitMQ"
  helm upgrade --install rabbitmq "$K8S/charts/rabbitmq" -n rabbitmq --create-namespace \
    -f "$ENV_DIR/rabbitmq.values.yaml" --wait --timeout 15m

  if [[ -f "$ENV_DIR/minio.values.yaml" ]]; then
    log "MinIO"
    helm dependency update "$K8S/charts/minio" >/dev/null
    helm upgrade --install minio "$K8S/charts/minio" -n minio --create-namespace \
      -f "$ENV_DIR/minio.values.yaml" --wait --timeout 15m
  else
    log "MinIO skipped (STORAGE_TYPE is not 'local')"
  fi
}

# --------------------------------------------------------------- core ---
phase_core() {
  # The Keycloak image keeps no client secrets in the realm export — it ships
  # placeholders — and its entrypoint refuses to start unless both are supplied.
  # The generator does not emit them, so they are generated once per environment
  # here and appended to SECRETS.env alongside everything else.
  #
  # KC_LARAVEL_BACKEND_SECRET is also the `laravel-backend` client secret the
  # realm import installs, i.e. exactly the value the post-install step asks you
  # to copy into webBack.secrets.KEYCLOAK_CLIENT_SECRET.
  local kc_secrets="$ENV_DIR/keycloak-secrets.env"
  if [[ ! -f "$kc_secrets" ]]; then
    {
      echo "KC_LARAVEL_BACKEND_SECRET=$(openssl rand -base64 24 | tr -d '/+=')"
      echo "KC_REALM_MANAGEMENT_SECRET=$(openssl rand -base64 24 | tr -d '/+=')"
    } > "$kc_secrets"
    chmod 600 "$kc_secrets"
    cat "$kc_secrets" >> "$ENV_DIR/SECRETS.env"
  fi
  # shellcheck disable=SC1090
  source "$kc_secrets"

  log "pid-gijon-core (web-back disabled — it needs Keycloak configured first)"
  helm upgrade --install pid-gijon "$K8S/charts/pid-gijon-core" -n pid-gijon --create-namespace \
    -f "$ENV_DIR/pid-gijon-core.values.yaml" \
    --set components.webBack.enabled=false \
    --set "components.keycloak.secrets.KC_LARAVEL_BACKEND_SECRET=$KC_LARAVEL_BACKEND_SECRET" \
    --set "components.keycloak.secrets.KC_REALM_MANAGEMENT_SECRET=$KC_REALM_MANAGEMENT_SECRET" \
    --set "components.keycloak.config.BACKEND_URL=http://web-back:80" \
    --wait --timeout 20m

  cat <<EOF

$(printf '\033[1;33m')Manual step before the next phase.$(printf '\033[0m')

Now do the Keycloak and Realtime post-install, following
  deploy/docs/06-post-install.md

In short: check the realm and clients the Keycloak image imported, then copy
two values into
  $ENV_DIR/pid-gijon-core.values.yaml
replacing the REPLACE_AFTER_KEYCLOAK_SETUP placeholders —
  * the realm's RS256 public key   (Realm settings -> Keys -> RS256)
  * the laravel-backend client secret — which is KC_LARAVEL_BACKEND_SECRET in
    $ENV_DIR/keycloak-secrets.env, the value this phase just installed

Then:
  deploy/k3s-deploy.sh --env $ENV_NAME --phase webback
EOF
}

# ------------------------------------------------------------ webback ---
phase_webback() {
  if grep -q REPLACE_AFTER_KEYCLOAK_SETUP "$ENV_DIR/pid-gijon-core.values.yaml" 2>/dev/null; then
    die "pid-gijon-core.values.yaml still has REPLACE_AFTER_KEYCLOAK_SETUP placeholders.
       Do the Keycloak post-install first — docs/06-post-install.md."
  fi
  # shellcheck disable=SC1090
  source "$ENV_DIR/keycloak-secrets.env"
  log "Enabling web-back (it runs the migrations as an init container)"
  helm upgrade pid-gijon "$K8S/charts/pid-gijon-core" -n pid-gijon \
    -f "$ENV_DIR/pid-gijon-core.values.yaml" \
    --set "components.keycloak.secrets.KC_LARAVEL_BACKEND_SECRET=$KC_LARAVEL_BACKEND_SECRET" \
    --set "components.keycloak.secrets.KC_REALM_MANAGEMENT_SECRET=$KC_REALM_MANAGEMENT_SECRET" \
    --set "components.keycloak.config.BACKEND_URL=http://web-back:80" \
    --wait --timeout 20m

  cat <<EOF

Verify with the bundled suite:
  cd $K8S && ./tests/run-tests.sh $ENV_NAME

EOF
}

case "$PHASE" in
  config)  phase_config ;;
  data)    phase_data ;;
  core)    phase_core ;;
  webback) phase_webback ;;
  all)     phase_config; phase_data; phase_core ;;
  *) die "unknown phase: $PHASE (config|data|core|webback|all)" ;;
esac
