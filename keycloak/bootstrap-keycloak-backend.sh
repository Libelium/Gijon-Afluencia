#!/bin/sh
if [ -z "${BACKEND_URL}" ]; then
  echo "ERROR: BACKEND_URL environment variable is not defined. Stopping container."
  exit 1
fi

# Client secrets. The realm import ships placeholders, never a value: an image that could boot
# with a guessable secret is an image whose tokens can be minted by anyone who read the source.
# Generate them once per installation with `openssl rand -base64 24`.
: "${KC_LARAVEL_BACKEND_SECRET:?is not defined. Generate one with 'openssl rand -base64 24' and set it before starting the container.}"
: "${KC_REALM_MANAGEMENT_SECRET:?is not defined. Generate one with 'openssl rand -base64 24' and set it before starting the container.}"

sed -i "s|__BACKEND_URL__|${BACKEND_URL}|g" /opt/keycloak/themes/pidtheme/login/theme.properties
sed -i "s|__KC_DEFAULT_LOCALE__|${KC_DEFAULT_LOCALE:-en}|g" /opt/keycloak/themes/pidtheme/login/theme.properties

# White-label brand colours, all optional.
# pidtheme-mobile inherits them via parent=pidtheme.
KC_BRAND_PRIMARY="${KC_BRAND_PRIMARY:-#7D00F4}"
KC_BRAND_SECONDARY="${KC_BRAND_SECONDARY:-#5800C0}"
KC_BRAND_INDIGO="${KC_BRAND_INDIGO:-#150D5F}"
for f in /opt/keycloak/themes/pidtheme/login/theme.properties \
         /opt/keycloak/themes/pidtheme/email/theme.properties; do
  sed -i "s|__KC_BRAND_PRIMARY__|${KC_BRAND_PRIMARY}|g" "$f"
  sed -i "s|__KC_BRAND_SECONDARY__|${KC_BRAND_SECONDARY}|g" "$f"
  sed -i "s|__KC_BRAND_INDIGO__|${KC_BRAND_INDIGO}|g" "$f"
done
echo "Brand colours: primary=${KC_BRAND_PRIMARY} secondary=${KC_BRAND_SECONDARY} indigo=${KC_BRAND_INDIGO}"

# Login parallax image: a URL or a file name in login/resources/img/. Unset => the bundled logo.
# Escaped because a URL may carry &, | or \, which sed would read as replacement syntax.
KC_BRAND_LOGIN_IMAGE_SED=$(printf '%s' "${KC_BRAND_LOGIN_IMAGE:-}" | sed -e 's/[&|\\]/\\&/g')
sed -i "s|__KC_BRAND_LOGIN_IMAGE__|${KC_BRAND_LOGIN_IMAGE_SED}|g" \
  /opt/keycloak/themes/pidtheme/login/theme.properties
echo "Login parallax image: ${KC_BRAND_LOGIN_IMAGE:-<none, using the bundled logo>}"

# Env-driven realm config (substituted into the import file before --import-realm):
#  - KC_LARAVEL_BACKEND_SECRET   : client secret of the `laravel-backend` confidential client
#  - KC_REALM_MANAGEMENT_SECRET  : client secret of the `realm-management` client
#  - KC_REGISTRATION_ALLOWED     : show register link + enable the register view (default off)
#  - KC_MOBILE_CLIENT_ENABLED    : enable the mobile public client (default off)
#  - KC_DEFAULT_LOCALE           : UI language for all theme views (es|en|ca|el|pt, default en)
#  - KC_APP_REDIRECT_URIS        : OAuth callback URLs (see below), default: KC_HOSTNAME
#  - KC_APP_WEB_ORIGINS          : CORS origins for those clients, default: KC_HOSTNAME
#  - KC_SMTP_*                   : mail server for the MFA code and password resets (see below)
REALM_FILE=/opt/keycloak/data/import/realm.json
LARAVEL_BACKEND_SECRET_SED=$(printf '%s' "${KC_LARAVEL_BACKEND_SECRET}" | sed -e 's/[&|\\]/\\&/g')
REALM_MANAGEMENT_SECRET_SED=$(printf '%s' "${KC_REALM_MANAGEMENT_SECRET}" | sed -e 's/[&|\\]/\\&/g')
sed -i "s|__KC_LARAVEL_BACKEND_SECRET__|${LARAVEL_BACKEND_SECRET_SED}|g" "$REALM_FILE"
sed -i "s|__KC_REALM_MANAGEMENT_SECRET__|${REALM_MANAGEMENT_SECRET_SED}|g" "$REALM_FILE"
sed -i "s|__KC_REGISTRATION_ALLOWED__|${KC_REGISTRATION_ALLOWED:-false}|g" "$REALM_FILE"
sed -i "s|__KC_MOBILE_CLIENT_ENABLED__|${KC_MOBILE_CLIENT_ENABLED:-false}|g" "$REALM_FILE"
sed -i "s|__KC_DEFAULT_LOCALE__|${KC_DEFAULT_LOCALE:-en}|g" "$REALM_FILE"

# ---------------------------------------------------------------------------
# OAuth callback URLs.
#
# The realm no longer ships the catch-all "/*" for the service clients
# (laravel-backend, laravel-backend-client, vue-frontend, dlm-client). "/*" is
# relative to the Keycloak origin, so it accepted a redirect to ANY path Keycloak
# serves; a single reflecting path there is enough to walk off with an
# authorization code.
#
# The default is the public Keycloak URL, which is exactly the redirect_uri the
# backend sends when it exchanges the code (KEYCLOAK_REDIRECT_URI = URL_KEYCLOAK
# = KC_HOSTNAME in the generated values). Set KC_APP_REDIRECT_URIS (and, if the
# browser needs them, KC_APP_WEB_ORIGINS) to a comma-separated list when a
# deployment needs more than that.
# ---------------------------------------------------------------------------
json_array_from_csv() {
  # "a,b" -> ["a","b"] ; "" -> []
  printf '%s' "$1" | awk -F, '{
    out = "[";
    for (i = 1; i <= NF; i++) {
      gsub(/^[ \t]+|[ \t]+$/, "", $i);
      if ($i == "") continue;
      if (out != "[") out = out ",";
      out = out "\"" $i "\"";
    }
    print out "]";
  }'
}

APP_REDIRECT_URIS=$(json_array_from_csv "${KC_APP_REDIRECT_URIS:-${KC_HOSTNAME:-}}")
APP_WEB_ORIGINS=$(json_array_from_csv "${KC_APP_WEB_ORIGINS:-${KC_HOSTNAME:-}}")

# An empty list (no KC_HOSTNAME, no KC_APP_REDIRECT_URIS) would leave every service
# client without a callback and break the code exchange, so stop here instead.
if [ -z "$APP_REDIRECT_URIS" ] || [ "$APP_REDIRECT_URIS" = "[]" ]; then
  echo "ERROR: no OAuth callback URL. Set KC_APP_REDIRECT_URIS (or KC_HOSTNAME) to the public Keycloak URL, the same value the backend uses as KEYCLOAK_REDIRECT_URI. Stopping container."
  exit 1
fi

sed -i "s|__KC_APP_REDIRECT_URIS__|${APP_REDIRECT_URIS}|g" "$REALM_FILE"
sed -i "s|__KC_APP_WEB_ORIGINS__|${APP_WEB_ORIGINS}|g" "$REALM_FILE"
echo "OAuth callback URLs: ${APP_REDIRECT_URIS}"

# ---------------------------------------------------------------------------
# SMTP.
#
# This channel carries the second-factor code and the password-reset links, so
# when it is configured at all it must be authenticated and encrypted. The realm
# no longer hard-codes auth:false: the flags are derived here and the container
# refuses to start on an unsafe combination.
#
#   KC_SMTP_HOST      mail server. Unset => no mail is configured (dev installs).
#   KC_SMTP_PORT      default 587 (submission + STARTTLS).
#   KC_SMTP_USER      REQUIRED when KC_SMTP_HOST is set.
#   KC_SMTP_PASSWORD  REQUIRED when KC_SMTP_HOST is set.
#   KC_SMTP_STARTTLS  default true. Set false only with KC_SMTP_SSL=true.
#   KC_SMTP_SSL       implicit TLS (port 465). Default false.
#   KC_SMTP_FROM      envelope sender. KC_SMTP_FROM_DISPLAY_NAME its label.
# ---------------------------------------------------------------------------
KC_SMTP_PORT="${KC_SMTP_PORT:-587}"
KC_SMTP_SSL="${KC_SMTP_SSL:-false}"
KC_SMTP_STARTTLS="${KC_SMTP_STARTTLS:-true}"
KC_SMTP_FROM="${KC_SMTP_FROM:-no-reply@pid.gijon.example}"
KC_SMTP_FROM_DISPLAY_NAME="${KC_SMTP_FROM_DISPLAY_NAME:-PID Gijon}"

if [ -n "${KC_SMTP_HOST:-}" ]; then
  : "${KC_SMTP_USER:?is not defined. The realm mail server carries the MFA code and the password-reset links, so it must authenticate. Set KC_SMTP_USER and KC_SMTP_PASSWORD, or leave KC_SMTP_HOST unset to run without mail.}"
  : "${KC_SMTP_PASSWORD:?is not defined. Set it together with KC_SMTP_USER.}"

  if [ "$KC_SMTP_STARTTLS" != "true" ] && [ "$KC_SMTP_SSL" != "true" ]; then
    echo "ERROR: SMTP would run in the clear (KC_SMTP_STARTTLS=false and KC_SMTP_SSL=false). That channel carries the second-factor code and the password-reset links. Stopping container."
    exit 1
  fi

  KC_SMTP_AUTH=true
  echo "SMTP: ${KC_SMTP_HOST}:${KC_SMTP_PORT} auth=true starttls=${KC_SMTP_STARTTLS} ssl=${KC_SMTP_SSL}"
else
  # No mail server configured: leave it unauthenticated but unreachable, and say so.
  KC_SMTP_HOST=""
  KC_SMTP_USER=""
  KC_SMTP_PASSWORD=""
  KC_SMTP_AUTH=false
  echo "SMTP: not configured (KC_SMTP_HOST unset). Password reset and the e-mail second factor will NOT work."
fi

SMTP_PASSWORD_SED=$(printf '%s' "${KC_SMTP_PASSWORD}" | sed -e 's/[&|\\]/\\&/g')
sed -i "s|__KC_SMTP_HOST__|${KC_SMTP_HOST}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_PORT__|${KC_SMTP_PORT}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_AUTH__|${KC_SMTP_AUTH}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_USER__|${KC_SMTP_USER}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_PASSWORD__|${SMTP_PASSWORD_SED}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_SSL__|${KC_SMTP_SSL}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_STARTTLS__|${KC_SMTP_STARTTLS}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_FROM__|${KC_SMTP_FROM}|g" "$REALM_FILE"
sed -i "s|__KC_SMTP_FROM_DISPLAY_NAME__|${KC_SMTP_FROM_DISPLAY_NAME}|g" "$REALM_FILE"

# Production mode, importing the realm from $REALM_FILE on first boot.
# REF: https://www.keycloak.org/server/importExport
exec /opt/keycloak/bin/kc.sh start --optimized --import-realm
