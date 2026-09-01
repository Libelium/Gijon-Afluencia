#!/usr/bin/env bash
# =============================================================================
# PID Gijón — environment generator
# =============================================================================
# Creates a deployment environment with freshly generated, consistently-wired
# credentials. Produces one ready-to-use Helm values file per chart plus a
# master SECRETS.env. The SAME generated password is written everywhere it is
# used (e.g. the Postgres "platformdb" role password lands in stackgres.values.yaml
# AND in pid-gijon-core's web-back secret), so the platform wires up correctly.
#
# Usage:
#   ./scripts/generate-env.sh <environment-name>
#
#   1st run : scaffolds environments/<name>/config.env (edit it, then re-run)
#   2nd run : renders values files + SECRETS.env (git-ignored)
#
# Re-running is safe: existing secrets in SECRETS.env are reused, so only newly
# introduced fields get generated.
# =============================================================================

set -eo pipefail

# --- pretty output ---------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()      { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()     { echo -e "${RED}[ERROR]${NC} $1" >&2; exit 1; }

# --- locate paths ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"
EXAMPLE_CONFIG="${REPO_ROOT}/environments/example/config.env.example"

# --- arguments -------------------------------------------------------------
ENV_NAME="${1:-}"
[ -n "$ENV_NAME" ] || die "Usage: $0 <environment-name>   (e.g. $0 prod)"

ENV_DIR="${REPO_ROOT}/environments/${ENV_NAME}"
CONFIG_FILE="${ENV_DIR}/config.env"
SECRETS_FILE="${ENV_DIR}/SECRETS.env"

command -v envsubst >/dev/null || die "envsubst not found. Install GNU gettext (e.g. 'apt-get install gettext-base' or 'brew install gettext')."
command -v openssl  >/dev/null || die "openssl not found."

# --- first run: scaffold config -------------------------------------------
if [ ! -f "$CONFIG_FILE" ]; then
    mkdir -p "$ENV_DIR"
    cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
    ok "Created ${CONFIG_FILE}"
    echo ""
    info "Next:"
    echo "  1. Edit ${CONFIG_FILE}"
    echo "  2. Re-run: $0 ${ENV_NAME}"
    exit 0
fi

# --- load existing secrets (for stable re-runs) then config ----------------
# shellcheck disable=SC1090
[ -f "$SECRETS_FILE" ] && source "$SECRETS_FILE"
# shellcheck disable=SC1090
source "$CONFIG_FILE"

# --- password generators ---------------------------------------------------
gen_password()  { openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 32; }
gen_long()      { openssl rand -base64 96 | tr -dc 'a-zA-Z0-9' | head -c 64; }
gen_hex()       { openssl rand -hex 32; }
gen_b64key()    { echo "base64:$(openssl rand -base64 32)"; }
gen_uuid()      { cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid;print(uuid.uuid4())'; }
# set VAR if currently empty: setdef VAR "$(generator)"
setdef() { local n="$1"; [ -n "${!n}" ] || printf -v "$n" '%s' "$2"; }

# --- defaults for non-secret config ---------------------------------------
PROJECT_NAME="${PROJECT_NAME:-$ENV_NAME}"
ENVIRONMENT="${ENVIRONMENT:-$ENV_NAME}"
BASE_DOMAIN="${BASE_DOMAIN:-example.com}"
GATEWAY_NAMESPACE="${GATEWAY_NAMESPACE:-gateway}"
GATEWAY_PUBLIC="${GATEWAY_PUBLIC:-public-gateway}"
APISIX_ENABLED="${APISIX_ENABLED:-false}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-}"
CONTEXT_URL="${CONTEXT_URL:-https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld}"
STORAGE_TYPE="${STORAGE_TYPE:-local}"
S3_BUCKET="${S3_BUCKET:-pid-gijon-storage}"
S3_REGION="${S3_REGION:-eu-west-1}"
S3_ENDPOINT="${S3_ENDPOINT:-}"
MONGO_USER="${MONGO_USER:-fiware-mongo-user}"
RABBITMQ_USER="${RABBITMQ_USER:-pid-gijon-user}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-pid-gijon}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
# Realm and public client the platform authenticates against. They must match
# what the Keycloak image imports (keycloak/realm.json) — override both in
# config.env if you build that image with different names.
KEYCLOAK_REALM="${KEYCLOAK_REALM:-pid-gijon}"
KEYCLOAK_PUBLIC_CLIENT="${KEYCLOAK_PUBLIC_CLIENT:-pid-gijon-client}"

# Colores corporativos de la pagina de inicio de sesion de Keycloak. El tema los lee de estas
# tres variables de entorno y con ellas compone el degradado del fondo (indigo -> secondary ->
# primary) y los tintes derivados. Vacias = los violetas que trae el tema por defecto.
# KC_BRAND_LOGIN_IMAGE admite una URL absoluta o el nombre de un fichero de
# keycloak/pidtheme/login/resources/img/; vacia = el logo.png incluido en la imagen.
KC_BRAND_PRIMARY="${KC_BRAND_PRIMARY:-}"
KC_BRAND_SECONDARY="${KC_BRAND_SECONDARY:-}"
KC_BRAND_INDIGO="${KC_BRAND_INDIGO:-}"
KC_BRAND_LOGIN_IMAGE="${KC_BRAND_LOGIN_IMAGE:-}"
KC_IMPERSONATION_USERNAME="${KC_IMPERSONATION_USERNAME:-admin_qc@${BASE_DOMAIN}}"
MAIL_HOST="${MAIL_HOST:-}"
MAIL_FROM="${MAIL_FROM:-no-reply@${BASE_DOMAIN}}"

for t in TAG_AETHER_LINK TAG_FIWARE_MANAGER TAG_QUEUES_CONSUMER TAG_WEB_BACK TAG_KEYCLOAK TAG_FRONTEND; do
    [ -n "${!t}" ] || printf -v "$t" '%s' "latest"
done

# Public hostnames (auto-derive when blank).
DOMAIN_API="${DOMAIN_API:-api.${PROJECT_NAME}.${BASE_DOMAIN}}"
DOMAIN_KEYCLOAK="${DOMAIN_KEYCLOAK:-kc.${PROJECT_NAME}.${BASE_DOMAIN}}"
DOMAIN_FRONTEND="${DOMAIN_FRONTEND:-app.${PROJECT_NAME}.${BASE_DOMAIN}}"
DOMAIN_FIWARE="${DOMAIN_FIWARE:-fiware.${PROJECT_NAME}.${BASE_DOMAIN}}"
DOMAIN_APISIX="${DOMAIN_APISIX:-fiware-secured.${PROJECT_NAME}.${BASE_DOMAIN}}"

# --- in-cluster vs external endpoints --------------------------------------
PG_HOST="${EXTERNAL_POSTGRES_HOST:-pid-gijon-postgres.postgres.svc.cluster.local}"
PG_PORT="${EXTERNAL_POSTGRES_PORT:-5432}"
MONGO_HOST="${EXTERNAL_MONGO_HOST:-mongodb-0.mongo-headless.mongodb.svc.cluster.local}"
MONGO_PORT="${EXTERNAL_MONGO_PORT:-27017}"
RABBITMQ_HOST="${EXTERNAL_RABBITMQ_HOST:-pid-gijon.rabbitmq.svc.cluster.local}"
RABBITMQ_PORT="${EXTERNAL_RABBITMQ_PORT:-5672}"
RABBITMQ_SECURITY="${EXTERNAL_RABBITMQ_SECURITY:-amqp}"

URL_API="https://${DOMAIN_API}"
URL_KEYCLOAK="https://${DOMAIN_KEYCLOAK}"
URL_FRONTEND="https://${DOMAIN_FRONTEND}"

# Cartografia de la interfaz web. OpenStreetMap por defecto: no requiere clave. La
# atribucion es obligatoria por sus terminos de uso (ver NOTICE.md).
#
# El valor por defecto va en su propia variable entrecomillada, y NO en linea como
# "${MAP_TILES_URL:-https://{s}.tile...}": ahi el primer } —el de {s}— cierra la
# expansion, y bash produce "https://{s.tile.openstreetmap.org/{z}/{x}/{y}.png}",
# una plantilla que Leaflet no sabe resolver y que deja el mapa sin teselas.
DEFAULT_MAP_TILES_URL='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
MAP_TILES_URL="${MAP_TILES_URL:-$DEFAULT_MAP_TILES_URL}"
MAP_TILES_ATTRIBUTION="${MAP_TILES_ATTRIBUTION:-&copy; colaboradores de OpenStreetMap}"
MAP_DEFAULT_CENTER="${MAP_DEFAULT_CENTER:-43.5322,-5.6611}"
MAP_DEFAULT_ZOOM="${MAP_DEFAULT_ZOOM:-13}"

# --- generate secrets (only if not already set) ----------------------------
info "Generating any missing secrets..."
setdef DB_PASSWORD_PLATFORMDB        "$(gen_password)"
setdef DB_PASSWORD_KEYCLOAK      "$(gen_password)"
setdef DB_PASSWORD_REALTIME      "$(gen_password)"
setdef DB_PASSWORD_AIRFLOW       "$(gen_password)"
setdef OTE_WEBHOOK_TOKEN         "$(gen_password)"
setdef MONGO_PASSWORD            "$(gen_password)"
setdef RABBITMQ_PASSWORD         "$(gen_password)"
setdef LARAVEL_APP_KEY           "$(gen_b64key)"
setdef FILE_ENCRYPTION_KEY       "$(gen_hex)"
setdef GENERIC_ENCRYPTION_KEY    "$(gen_hex)"
setdef ENCRYPTION_ENTITIES_KEY   "$(gen_hex)"
setdef API_GATEWAY_SECRET        "$(gen_password)"
# Secretos compartidos de los endpoints fail-closed (GDTIS-PT01-SEC-017/044/019).
# Sin valor, esos servicios responden 503 a proposito en vez de aceptar a cualquiera.
setdef QUEUES_CONSUMER_API_TOKEN "$(gen_password)"
setdef ANOMALY_STATE_HMAC_KEY    "$(gen_hex)"
setdef KC_ADMIN_PASSWORD         "$(gen_password)"
setdef KC_IMPERSONATION_CLIENT_SECRET "$(gen_password)"
setdef KC_IMPERSONATION_PASSWORD "$(gen_password)"
# APISIX Admin API key (only used by the optional apisix component).
setdef APISIX_ADMIN_KEY          "$(openssl rand -hex 16)"

# Filled in after the one-time Keycloak realm setup (docs/06-post-install.md).
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-REPLACE_AFTER_KEYCLOAK_SETUP}"
KEYCLOAK_PUBLIC_KEY="${KEYCLOAK_PUBLIC_KEY:-REPLACE_AFTER_KEYCLOAK_SETUP}"

# Optional external credentials (user-provided in config.env).
MAIL_USERNAME="${MAIL_USERNAME:-}"
MAIL_PASSWORD="${MAIL_PASSWORD:-}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-}"
S3_SECRET_KEY="${S3_SECRET_KEY:-}"

# --- storage wiring --------------------------------------------------------
if [ "$STORAGE_TYPE" = "local" ]; then
    setdef MINIO_ROOT_PASSWORD "$(gen_password)"
    setdef MINIO_ACCESS_KEY    "$(gen_password)"
    setdef MINIO_SECRET_KEY    "$(gen_password)"
    MINIO_ENDPOINT="minio.minio.svc.cluster.local:9000"
    STORAGE_ENDPOINT="http://${MINIO_ENDPOINT}"
    STORAGE_PATH_STYLE="true"
    STORAGE_ACCESS_KEY="$MINIO_ACCESS_KEY"
    STORAGE_SECRET_KEY="$MINIO_SECRET_KEY"
    # keep external-S3 secret fields empty in the rendered values
    S3_ACCESS_KEY=""; S3_SECRET_KEY=""
else
    [ -n "$S3_ACCESS_KEY" ] && [ -n "$S3_SECRET_KEY" ] || \
        warn "STORAGE_TYPE=s3 but S3_ACCESS_KEY/S3_SECRET_KEY are empty in config.env."
    MINIO_ENDPOINT=""; MINIO_ACCESS_KEY=""; MINIO_SECRET_KEY=""; MINIO_ROOT_PASSWORD=""
    STORAGE_ENDPOINT="$S3_ENDPOINT"
    [ -n "$S3_ENDPOINT" ] && STORAGE_PATH_STYLE="true" || STORAGE_PATH_STYLE="false"
    STORAGE_ACCESS_KEY="$S3_ACCESS_KEY"
    STORAGE_SECRET_KEY="$S3_SECRET_KEY"
fi
ok "Secrets ready"

# --- verification-suite wiring (tests.env) ----------------------------------
# Platform admin used by the verification suite to log in. Defaults to the
# admin user the platform's Keycloak realm seeds on first install; override in
# config.env if your installation uses a different admin login.
TESTS_ADMIN_USERNAME="${TESTS_ADMIN_USERNAME:-admin@${BASE_DOMAIN}}"

# Operator-supplied verification values are NOT generated here — they are
# preserved across re-runs (like SECRETS.env), so regenerating an environment
# never wipes a filled-in admin password or a pinned API key. Precedence:
# config.env > the existing tests.env > empty.
#   ADMIN_PASSWORD : set by the Keycloak realm import, not this installer.
#   DATA_API_KEY / TENANT : normally auto-discovered by the suite; pin only for
#   non-standard installs.
read_existing_tests_env() {  # read_existing_tests_env <KEY> -> current value or ""
    [ -f "${ENV_DIR}/tests.env" ] || return 0
    grep -E "^$1=" "${ENV_DIR}/tests.env" | tail -n1 | cut -d= -f2-
}
TESTS_ADMIN_PASSWORD="${TESTS_ADMIN_PASSWORD:-$(read_existing_tests_env ADMIN_PASSWORD)}"
TESTS_DATA_API_KEY="${TESTS_DATA_API_KEY:-$(read_existing_tests_env DATA_API_KEY)}"
TESTS_TENANT="${TESTS_TENANT:-$(read_existing_tests_env TENANT)}"
# The suite only checks the bundled data charts that were actually deployed.
TESTS_CHECK_POSTGRES=$([ -n "${EXTERNAL_POSTGRES_HOST:-}" ] && echo false || echo true)
TESTS_CHECK_MONGODB=$([ -n "${EXTERNAL_MONGO_HOST:-}" ] && echo false || echo true)
TESTS_CHECK_RABBITMQ=$([ -n "${EXTERNAL_RABBITMQ_HOST:-}" ] && echo false || echo true)
TESTS_CHECK_MINIO=$([ "$STORAGE_TYPE" = "local" ] && echo true || echo false)

# --- Airflow verification (optional add-on) ---------------------------------
# Airflow is deployed separately (its own Airflow deployment), not by this
# installer, so its settings are operator-supplied and preserved across re-runs.
# Leave TESTS_AIRFLOW_URL empty to skip the whole Airflow stage. The apikey and
# tenant feed the test DAG's IoT Agent POST; everything else has a sane default.
TESTS_AIRFLOW_URL="${TESTS_AIRFLOW_URL:-$(read_existing_tests_env AIRFLOW_URL)}"
TESTS_AIRFLOW_USERNAME="${TESTS_AIRFLOW_USERNAME:-$(read_existing_tests_env AIRFLOW_USERNAME)}"
TESTS_AIRFLOW_PASSWORD="${TESTS_AIRFLOW_PASSWORD:-$(read_existing_tests_env AIRFLOW_PASSWORD)}"
TESTS_AIRFLOW_NAMESPACE="${TESTS_AIRFLOW_NAMESPACE:-airflow}"
TESTS_AIRFLOW_IOTA_URL="${TESTS_AIRFLOW_IOTA_URL:-http://iot-agent-json.${PLATFORM_NAMESPACE:-pid-gijon}.svc.cluster.local:7896/iot/json}"
TESTS_AIRFLOW_IOTA_APIKEY="${TESTS_AIRFLOW_IOTA_APIKEY:-$(read_existing_tests_env AIRFLOW_VAR_IOTA_APIKEY)}"
TESTS_AIRFLOW_DATAMODEL="${TESTS_AIRFLOW_DATAMODEL:-Device}"
TESTS_AIRFLOW_TENANT="${TESTS_AIRFLOW_TENANT:-${TESTS_TENANT}}"
TESTS_AIRFLOW_SCOPE="${TESTS_AIRFLOW_SCOPE:-/}"
TESTS_AIRFLOW_ENTITY_NAME="${TESTS_AIRFLOW_ENTITY_NAME:-airflow-iota-test}"

# --- export everything for envsubst ----------------------------------------
VARS=(PROJECT_NAME ENVIRONMENT IMAGE_REGISTRY GATEWAY_NAMESPACE GATEWAY_PUBLIC
  APISIX_ENABLED DOMAIN_APISIX APISIX_ADMIN_KEY
  CONTEXT_URL TAG_AETHER_LINK TAG_FIWARE_MANAGER
  TAG_QUEUES_CONSUMER TAG_WEB_BACK TAG_KEYCLOAK TAG_FRONTEND PG_HOST PG_PORT
  MONGO_HOST MONGO_PORT MONGO_USER MONGO_PASSWORD RABBITMQ_HOST RABBITMQ_PORT
  RABBITMQ_SECURITY RABBITMQ_VHOST RABBITMQ_USER RABBITMQ_PASSWORD
  KEYCLOAK_ADMIN_USER KEYCLOAK_REALM KEYCLOAK_PUBLIC_CLIENT S3_BUCKET S3_REGION STORAGE_TYPE
  KC_BRAND_PRIMARY KC_BRAND_SECONDARY KC_BRAND_INDIGO KC_BRAND_LOGIN_IMAGE
  MINIO_ENDPOINT STORAGE_ENDPOINT STORAGE_PATH_STYLE STORAGE_ACCESS_KEY
  STORAGE_SECRET_KEY S3_ACCESS_KEY S3_SECRET_KEY MINIO_ACCESS_KEY MINIO_SECRET_KEY
  MINIO_ROOT_PASSWORD DOMAIN_API DOMAIN_KEYCLOAK DOMAIN_FIWARE
  DOMAIN_FRONTEND URL_API URL_KEYCLOAK URL_FRONTEND
  MAP_TILES_URL MAP_TILES_ATTRIBUTION MAP_DEFAULT_CENTER MAP_DEFAULT_ZOOM MAIL_HOST MAIL_FROM
  MAIL_USERNAME MAIL_PASSWORD DB_PASSWORD_PLATFORMDB DB_PASSWORD_KEYCLOAK
  DB_PASSWORD_REALTIME DB_PASSWORD_AIRFLOW OTE_WEBHOOK_TOKEN
  QUEUES_CONSUMER_API_TOKEN ANOMALY_STATE_HMAC_KEY
  LARAVEL_APP_KEY
  FILE_ENCRYPTION_KEY GENERIC_ENCRYPTION_KEY ENCRYPTION_ENTITIES_KEY API_GATEWAY_SECRET
  KC_ADMIN_PASSWORD KEYCLOAK_CLIENT_SECRET
  KEYCLOAK_PUBLIC_KEY KC_IMPERSONATION_CLIENT_SECRET KC_IMPERSONATION_USERNAME
  KC_IMPERSONATION_PASSWORD TESTS_ADMIN_USERNAME TESTS_ADMIN_PASSWORD
  TESTS_DATA_API_KEY TESTS_TENANT TESTS_CHECK_POSTGRES
  TESTS_CHECK_MONGODB TESTS_CHECK_RABBITMQ TESTS_CHECK_MINIO
  TESTS_AIRFLOW_URL TESTS_AIRFLOW_USERNAME TESTS_AIRFLOW_PASSWORD
  TESTS_AIRFLOW_NAMESPACE TESTS_AIRFLOW_IOTA_URL TESTS_AIRFLOW_IOTA_APIKEY
  TESTS_AIRFLOW_DATAMODEL TESTS_AIRFLOW_TENANT TESTS_AIRFLOW_SCOPE
  TESTS_AIRFLOW_ENTITY_NAME)
export "${VARS[@]}"
SUBST=""; for v in "${VARS[@]}"; do SUBST+="\${$v} "; done

render() {  # render <template> <output>
    envsubst "$SUBST" < "${TEMPLATES_DIR}/$1" > "${ENV_DIR}/$2"
    ok "  -> environments/${ENV_NAME}/$2"
}

# --- render values files ---------------------------------------------------
echo ""
info "Rendering Helm values into environments/${ENV_NAME}/ ..."

if [ -n "${EXTERNAL_POSTGRES_HOST:-}" ]; then
    warn "  Postgres: external (${EXTERNAL_POSTGRES_HOST}) — skipping stackgres.values.yaml"
else
    render stackgres.values.yaml.tpl stackgres.values.yaml
fi

if [ -n "${EXTERNAL_MONGO_HOST:-}" ]; then
    warn "  MongoDB: external (${EXTERNAL_MONGO_HOST}) — skipping mongodb.values.yaml"
else
    render mongodb.values.yaml.tpl mongodb.values.yaml
fi

if [ -n "${EXTERNAL_RABBITMQ_HOST:-}" ]; then
    warn "  RabbitMQ: external (${EXTERNAL_RABBITMQ_HOST}) — skipping rabbitmq.values.yaml"
else
    render rabbitmq.values.yaml.tpl rabbitmq.values.yaml
fi

if [ "$STORAGE_TYPE" = "local" ]; then
    render minio.values.yaml.tpl minio.values.yaml
else
    warn "  Storage: external S3 — skipping minio.values.yaml"
fi

render pid-gijon-core.values.yaml.tpl pid-gijon-core.values.yaml

# Optional APISIX FIWARE gateway (opt-in via APISIX_ENABLED).
if [ "$APISIX_ENABLED" = "true" ]; then
    render apisix.values.yaml.tpl apisix.values.yaml
else
    warn "  APISIX: disabled (APISIX_ENABLED!=true) — skipping apisix.values.yaml"
fi

# Verification-suite config — pre-wired so ./tests/run-tests.sh works without
# manual setup when you deploy with the default arguments.
render tests.env.tpl tests.env
chmod 600 "${ENV_DIR}/tests.env"

# Realtime tenant setup (post-install 6.2) — a ready-to-run script with this
# environment's real values that mints the admin JWT and creates the tenant.
# Embeds secrets, so chmod 700 (executable + owner-only), like SECRETS.env.

# --- write SECRETS.env -----------------------------------------------------
{
  echo "# PID Gijón — generated secrets, environment: ${ENV_NAME}"
  echo "# KEEP SAFE. Do not commit. Store in your password manager / vault."
  echo ""
  for v in DB_PASSWORD_PLATFORMDB DB_PASSWORD_KEYCLOAK DB_PASSWORD_REALTIME \
           DB_PASSWORD_AIRFLOW OTE_WEBHOOK_TOKEN \
           QUEUES_CONSUMER_API_TOKEN ANOMALY_STATE_HMAC_KEY \
           MONGO_USER MONGO_PASSWORD RABBITMQ_USER RABBITMQ_PASSWORD RABBITMQ_VHOST \
           MINIO_ROOT_PASSWORD MINIO_ACCESS_KEY MINIO_SECRET_KEY \
           S3_ACCESS_KEY S3_SECRET_KEY \
           LARAVEL_APP_KEY FILE_ENCRYPTION_KEY GENERIC_ENCRYPTION_KEY \
           ENCRYPTION_ENTITIES_KEY API_GATEWAY_SECRET \
           KEYCLOAK_ADMIN_USER KC_ADMIN_PASSWORD \
           KEYCLOAK_CLIENT_SECRET KEYCLOAK_PUBLIC_KEY \
           KC_IMPERSONATION_USERNAME KC_IMPERSONATION_PASSWORD KC_IMPERSONATION_CLIENT_SECRET \
           APISIX_ADMIN_KEY \
           MAIL_USERNAME MAIL_PASSWORD; do
    printf '%s=%s\n' "$v" "${!v}"
  done
} > "$SECRETS_FILE"
chmod 600 "$SECRETS_FILE"
ok "  -> environments/${ENV_NAME}/SECRETS.env (chmod 600)"

# --- summary ---------------------------------------------------------------
echo ""
echo "=============================================================="
echo "  Environment '${ENV_NAME}' ready"
echo "=============================================================="
echo "  Storage:   ${STORAGE_TYPE}"
echo "  Postgres:  ${PG_HOST}:${PG_PORT}"
echo "  MongoDB:   ${MONGO_HOST}:${MONGO_PORT}"
echo "  RabbitMQ:  ${RABBITMQ_HOST}:${RABBITMQ_PORT} (vhost ${RABBITMQ_VHOST})"
echo "  Keycloak:  ${URL_KEYCLOAK}"
echo "  API:       https://${DOMAIN_API}"
[ "$APISIX_ENABLED" = "true" ] && echo "  APISIX:    https://${DOMAIN_APISIX} (optional FIWARE gateway)"
echo ""
warn "Store environments/${ENV_NAME}/SECRETS.env safely. It is git-ignored."
info "Next: follow the deployment steps in README.md."
info "After deploying, verify the platform: ./tests/run-tests.sh ${ENV_NAME}"
echo ""
