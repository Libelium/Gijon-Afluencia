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
REALM_FILE=/opt/keycloak/data/import/realm.json
LARAVEL_BACKEND_SECRET_SED=$(printf '%s' "${KC_LARAVEL_BACKEND_SECRET}" | sed -e 's/[&|\\]/\\&/g')
REALM_MANAGEMENT_SECRET_SED=$(printf '%s' "${KC_REALM_MANAGEMENT_SECRET}" | sed -e 's/[&|\\]/\\&/g')
sed -i "s|__KC_LARAVEL_BACKEND_SECRET__|${LARAVEL_BACKEND_SECRET_SED}|g" "$REALM_FILE"
sed -i "s|__KC_REALM_MANAGEMENT_SECRET__|${REALM_MANAGEMENT_SECRET_SED}|g" "$REALM_FILE"
sed -i "s|__KC_REGISTRATION_ALLOWED__|${KC_REGISTRATION_ALLOWED:-false}|g" "$REALM_FILE"
sed -i "s|__KC_MOBILE_CLIENT_ENABLED__|${KC_MOBILE_CLIENT_ENABLED:-false}|g" "$REALM_FILE"
sed -i "s|__KC_DEFAULT_LOCALE__|${KC_DEFAULT_LOCALE:-en}|g" "$REALM_FILE"

# Production mode, importing the realm from $REALM_FILE on first boot.
# REF: https://www.keycloak.org/server/importExport
exec /opt/keycloak/bin/kc.sh start --optimized --import-realm
