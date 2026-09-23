#!/bin/sh
#
# Escribe /usr/share/nginx/html/config.js con la configuracion tomada de las variables de
# entorno del contenedor, y despues arranca nginx.
#
# Por que existe: las variables VITE_* se incrustan en el paquete al compilar, asi que una
# imagen construida para preproduccion no vale para produccion. Este fichero rompe esa
# atadura: la misma imagen se despliega en cualquier entorno cambiando solo sus variables.
#
# Se acepta tanto el nombre con prefijo (VITE_API_BASE_URL) como el nombre corto
# (API_BASE_URL). El corto es el recomendado en el contenedor: el prefijo VITE_ solo tiene
# sentido en tiempo de compilacion y confunde en una variable de ejecucion.
#
# Solo se escriben las claves con valor. Una clave ausente en config.js deja que la
# aplicacion caiga en el valor incrustado al compilar, que puede ser el correcto.
#
# ATENCION: config.js lo descarga cualquier visitante. Vale para URL, identificadores
# publicos y parametros de mapa. Jamas para una credencial, un secreto de cliente OIDC o
# un token.
set -eu

TARGET="${APP_CONFIG_FILE:-/usr/share/nginx/html/config.js}"

# Claves publicadas en window.__APP_CONFIG__, con el nombre corto que tambien se acepta.
# Se conserva el nombre VITE_* como clave para que la lectura en la aplicacion sea un
# reemplazo directo de import.meta.env. Ver la seccion «Pendiente» de docs/deployment.md.
KEYS='VITE_API_BASE_URL:API_BASE_URL
VITE_OIDC_URL:OIDC_URL
VITE_OIDC_REALM:OIDC_REALM
VITE_OIDC_CLIENT_ID:OIDC_CLIENT_ID
VITE_OIDC_REDIRECT_URI:OIDC_REDIRECT_URI
VITE_MAP_TILES_URL:MAP_TILES_URL
VITE_MAP_TILES_URL_DARK:MAP_TILES_URL_DARK
VITE_MAP_TILES_ATTRIBUTION:MAP_TILES_ATTRIBUTION
VITE_MAP_TILES_ATTRIBUTION_DARK:MAP_TILES_ATTRIBUTION_DARK
VITE_MAP_DEFAULT_CENTER:MAP_DEFAULT_CENTER
VITE_MAP_DEFAULT_ZOOM:MAP_DEFAULT_ZOOM
VITE_REALTIME_URL:REALTIME_URL
VITE_DATA_SCOPE_PREFERENCE_KEY:DATA_SCOPE_PREFERENCE_KEY
VITE_ALARM_ENTITY_TYPE:ALARM_ENTITY_TYPE
VITE_ACCESSIBILITY_CONTACT:ACCESSIBILITY_CONTACT'

log() { printf 'entrypoint: %s\n' "$1" >&2; }

read_var() { eval "printf '%s' \"\${$1-}\""; }

# Escapa lo que rompe una cadena JavaScript. Los saltos de linea se eliminan: ningun valor
# de configuracion los lleva, y colarlos permitiria inyectar codigo en config.js.
escape() {
  printf '%s' "$1" | tr -d '\n\r' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e "s/</\\\\u003c/g"
}

# La prueba va en un subshell a proposito: un fallo de redireccion sobre un builtin
# especial termina el shell, y `[ -w ... ]` miente sobre un sistema de ficheros de solo
# lectura. Intentar la escritura de verdad y aislarla es lo unico fiable.
if ! ( : >>"$TARGET" ) 2>/dev/null; then
  log "AVISO: no se puede escribir $TARGET (¿sistema de ficheros de solo lectura?)."
  log 'Se sirve la configuracion incrustada al compilar. Las variables del contenedor se ignoran.'
  exec "$@"
fi

BODY=''
COUNT=0
SEP=''
for entry in $KEYS; do
  key=${entry%%:*}
  short=${entry#*:}

  value=$(read_var "$key")
  [ -n "$value" ] || value=$(read_var "$short")
  [ -n "$value" ] || continue

  BODY="${BODY}${SEP}
  \"${key}\": \"$(escape "$value")\""
  SEP=','
  COUNT=$((COUNT + 1))
done

{
  echo '/* Generado por deploy/entrypoint.sh en cada arranque del contenedor. No editar a mano. */'
  printf 'window.__APP_CONFIG__ = Object.freeze({%s\n});\n' "$BODY"
} >"$TARGET"

if [ "$COUNT" -eq 0 ]; then
  log 'AVISO: ninguna variable de configuracion definida; config.js va vacio.'
  log 'La aplicacion usara los valores incrustados al compilar la imagen.'
else
  log "config.js generado con $COUNT clave(s)."
fi

exec "$@"
