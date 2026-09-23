#!/usr/bin/env bash
#
# Post-instalación de Keycloak, entre las fases `core` y `webback`.
#
# Automatiza el único paso manual del despliegue (docs/06-post-install.md §6.1.c):
# rellena en el values del entorno los dos valores que el generador dejó como
# REPLACE_AFTER_KEYCLOAK_SETUP, tomándolos del realm ya en marcha:
#
#   - KEYCLOAK_PUBLIC_KEY    : clave pública RS256 del realm (endpoint del realm).
#   - KEYCLOAK_CLIENT_SECRET : secreto del cliente confidencial `laravel-backend`.
#                              Cuando el realm viene de la importación de la imagen
#                              es exactamente KC_LARAVEL_BACKEND_SECRET de
#                              environments/<env>/keycloak-secrets.env, así que se
#                              lee de ahí en lugar de la consola.
#
# Estos dos valores alimentan la validación de JWT del backend; por eso web-back
# se activa solo después de este paso.
#
# Uso (desde la raíz del repositorio):
#   deploy/kc-postinstall.sh <env>        # p. ej. deploy/kc-postinstall.sh gijon
#   deploy/k3s-deploy.sh --env <env> --phase webback
#
# Requisitos en la máquina: kubectl apuntando al clúster, curl y python3.
# Idempotente: se puede reejecutar.
#
set -euo pipefail

ENV="${1:-}"
[ -n "$ENV" ] || { echo "Uso: $0 <env>   (p. ej. $0 gijon)"; exit 2; }

NS="pid-gijon"
VALUES="deploy/environments/${ENV}/pid-gijon-core.values.yaml"
KCSECRETS="deploy/environments/${ENV}/keycloak-secrets.env"

[ -f "$VALUES" ]    || { echo "ERROR: no existe $VALUES (¿ejecutaste las fases config y core?)"; exit 1; }
[ -f "$KCSECRETS" ] || { echo "ERROR: no existe $KCSECRETS"; exit 1; }

echo "1/3  Esperando a que Keycloak esté disponible..."
kubectl -n "$NS" rollout status deploy/keycloak --timeout=180s

echo "2/3  Obteniendo el secreto de laravel-backend y la clave pública del realm..."
CLIENT_SECRET="$(grep -E '^KC_LARAVEL_BACKEND_SECRET=' "$KCSECRETS" | head -1 | cut -d= -f2-)"
[ -n "$CLIENT_SECRET" ] || { echo "ERROR: KC_LARAVEL_BACKEND_SECRET no está en $KCSECRETS"; exit 1; }

# La clave pública RS256 se lee del endpoint del realm, con un port-forward temporal.
kubectl -n "$NS" port-forward svc/keycloak 18080:8080 >/dev/null 2>&1 &
PF=$!
trap 'kill "$PF" 2>/dev/null || true' EXIT
sleep 3
PUBKEY="$(curl -s --max-time 15 "http://localhost:18080/realms/${NS}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("public_key",""))')"
kill "$PF" 2>/dev/null || true
trap - EXIT
[ -n "$PUBKEY" ] || { echo "ERROR: no se pudo obtener la clave pública del realm ${NS}"; exit 1; }

echo "3/3  Escribiendo ambos valores en $VALUES ..."
python3 - "$VALUES" "$PUBKEY" "$CLIENT_SECRET" <<'PY'
import sys, re, io
path, pub, sec = sys.argv[1], sys.argv[2], sys.argv[3]
lines = io.open(path, encoding="utf-8").read().split("\n")

def set_key(key, value):
    pat = re.compile(r'^(\s*)' + re.escape(key) + r':\s*.*$')
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            lines[i] = f'{m.group(1)}{key}: "{value}"'
            return True
    return False

ok_pub = set_key("KEYCLOAK_PUBLIC_KEY", pub)
ok_sec = set_key("KEYCLOAK_CLIENT_SECRET", sec)
if not (ok_pub and ok_sec):
    sys.exit(f"ERROR: no se encontraron las claves en el values (public={ok_pub}, secret={ok_sec})")
io.open(path, "w", encoding="utf-8").write("\n".join(lines))
PY

if grep -E 'KEYCLOAK_(PUBLIC_KEY|CLIENT_SECRET):.*REPLACE_AFTER_KEYCLOAK_SETUP' "$VALUES" >/dev/null; then
  echo "ERROR: todavía queda REPLACE_AFTER_KEYCLOAK_SETUP en $VALUES"
  exit 1
fi

echo
echo "OK. Los dos valores están puestos en $VALUES."
echo "Activa el backend con:"
echo "    deploy/k3s-deploy.sh --env ${ENV} --phase webback"
