# apisix — pasarela API opcional para FIWARE

Apache APISIX como pasarela API delante de los endpoints FIWARE. Autentica cada petición contra
**Keycloak** (JWT) y autoriza cada escritura contra la API de permisos por tenant de **web-back**,
antes de encaminarla a los backends FIWARE (`iot-agent-json`, `orion-ld`).

Es un componente **que hay que activar expresamente**. **No** forma parte de la instalación por
defecto de la plataforma: sin él, la protección de FIWARE la resuelven directamente
`fiware-manager` y `web-back`. Despliégalo solo si quieres que APISIX termine y vigile el tráfico
FIWARE. Recorrido completo: [docs/07-apisix.md](../../docs/07-apisix.md).

## Qué despliega

| Recurso | Origen |
|---------|--------|
| Plano de datos de APISIX + controlador de ingress | chart `apisix` original (dependencia) |
| `IngressClass` (`apisix`) y su `GatewayProxy` (`apisix-config`) | chart original (`gatewayProxy.createDefault`) |
| Un `ApisixRoute` por cada entrada de `fiware.services` | `templates/apisix-routes.yaml` |
| Módulo Lua de permisos FIWARE (`ConfigMap`) | `templates/configmap-lua.yaml` |
| `Secret` / `ExternalSecret` del cliente de Keycloak | `templates/secret.yaml` |
| `HTTPRoute` sobre el `public-gateway` del clúster | `templates/httproute.yaml` |

> **Namespace:** despliega este chart en el namespace **`pid-gijon`**, el mismo que
> pid-gijon-core. Los backends de un `ApisixRoute` deben estar en el namespace de la propia ruta,
> así que ponerlos juntos permite que las rutas apunten directamente a `iot-agent-json`,
> `orion-ld` y `web-back`. Además, el `HTTPRoute` se engancha entonces a `public-gateway` usando
> los `allowedRoutes` de `pid-gijon` que ya existen, sin tocar el Gateway.

## Recorrido de una petición

```
cliente ──▶ public-gateway (Gateway API, TLS) ──▶ apisix-gateway
                                                      │ [1] openid-connect → valida el JWT (Keycloak)
                                                      │ [2] serverless-pre-function → web-back
                                                      │       POST /api/internal/check-fiware-write-permission
                                                      └─[3] proxy → iot-agent-json:4041 | orion-ld:1026
```

## Rutas

| Ruta | Backend | Métodos | Cabeceras obligatorias |
|------|---------|---------|------------------------|
| `/iot/devices`, `/iot/devices/*` | `iot-agent-json:4041` | GET POST PUT DELETE | `Fiware-Service` + `Fiware-ServicePath` |
| `/iot/services`, `/iot/services/*` | `iot-agent-json:4041` | GET POST PUT DELETE | `Fiware-Service` + `Fiware-ServicePath` |
| `/ngsi-ld/v1/*` | `orion-ld:1026` | GET POST PUT PATCH DELETE | `NGSILD-Tenant` |

Para añadir o cambiar rutas, edita `fiware.services` en tus valores (el `headerType`, `fiware` o
`ngsild`, elige las cabeceras de tenancy).

## Instalación

El camino recomendado usa el generador, que te conecta el secreto de cliente de Keycloak, la URL de
descubrimiento, el nombre de host y una clave de administración de APISIX recién generada:

```bash
# 1. Actívalo: pon APISIX_ENABLED=true en environments/<entorno>/config.env y luego
./scripts/generate-env.sh <entorno>       # genera environments/<entorno>/apisix.values.yaml

# 2. Descarga el subchart original de apisix
helm dependency update charts/apisix

# 3. Despliega en el namespace pid-gijon (después de pid-gijon-core y de la
#    configuración de Keycloak de una sola vez, en docs/06)
helm upgrade --install apisix charts/apisix -n pid-gijon \
  -f environments/<entorno>/apisix.values.yaml --wait
```

Como el chart se despliega en `pid-gijon`, su `HTTPRoute` se engancha a `public-gateway` con los
`allowedRoutes` que ya permiten el namespace `pid-gijon`: no hace falta tocar el Gateway. Véase
[docs/04-gateway-api.md](../../docs/04-gateway-api.md).

## Secretos: aquí no se versiona ninguno

`keycloak.clientSecret` y la clave de administración de APISIX
(`apisix.apisix.admin.credentials.admin`) están **vacíos** en `values.yaml` a propósito; el chart
falla al renderizar (`apisix.validateCredentials`) mientras no se aporten en el despliegue.
Súmalos con el generador, con `--set` o —para GitOps y producción— pon
`keycloak.useExternalSecret: true` para tomar las credenciales del cliente de Keycloak desde el
External Secrets Operator. Véanse [docs/05-secrets.md](../../docs/05-secrets.md) y el
[SECURITY.md](../../SECURITY.md) del repositorio.

> El cliente de Keycloak (`laravel-backend`) y su secreto son **los mismos** que usa `web-back`:
> reutiliza `KEYCLOAK_CLIENT_SECRET`, no crees un cliente nuevo.

## Valores principales

| Clave | Por defecto | Para qué |
|-------|-------------|----------|
| `fiware.namespace` | `pid-gijon` | Namespace de los backends FIWARE. |
| `fiware.services` | 3 rutas | Rutas que se generan (ver arriba). |
| `keycloak.clientId` | `laravel-backend` | Cliente OIDC (compartido con web-back). |
| `keycloak.clientSecret` | `""` | **Se aporta en el despliegue.** |
| `keycloak.discoveryUrl` | `""` | URL de descubrimiento OIDC (obligatoria). |
| `keycloak.useExternalSecret` | `false` | Tomar las credenciales del ESO. |
| `gatewayAPI.gateway` | `public-gateway` | Gateway padre al que engancharse. |
| `gatewayAPI.hostnames` | `[]` | Nombres de host públicos de la pasarela. |
| `apisix.enabled` | `true` | Desplegar el plano de datos y el controlador incluidos. |
| `apisix.apisix.admin.credentials.admin` | `""` | **Se aporta en el despliegue.** Clave de administración de APISIX. |
