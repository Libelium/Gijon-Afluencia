# 7. Opcional: pasarela API APISIX para FIWARE

[Apache APISIX](https://apisix.apache.org/) puede colocarse delante de los endpoints FIWARE como
pasarela API dedicada que **autentica** cada petición contra Keycloak (JWT) y **autoriza** cada
escritura contra la API de permisos por tenant de `web-back`, antes de encaminarla a
`iot-agent-json` u `orion-ld`.

Es un componente **opcional que hay que activar expresamente** (`charts/apisix`). **No** forma
parte de la instalación por defecto: de origen, la protección de FIWARE la resuelven directamente
`fiware-manager` y `web-back`. Activa APISIX cuando quieras una pasarela aparte que termine y
vigile el tráfico FIWARE en su propio nombre de host.

## Cuándo usarlo

| Usa APISIX si… | Sáltatelo si… |
|----------------|---------------|
| Quieres imponer JWT y autorización por tenant en el borde, antes de que las peticiones lleguen a los servicios FIWARE. | Te basta con lo que ya imponen `fiware-manager` y `web-back`. |
| Expones las APIs FIWARE en crudo (`/iot/*`, `/ngsi-ld/v1/*`) a clientes externos. | A FIWARE solo se llega por dentro o a través de `web-back`. |
| Quieres un único punto de paso auditado, con los plugins de APISIX (límite de tasa, métricas…). | Prefieres mantener al mínimo el número de piezas móviles. |

## Requisitos previos

Además de los requisitos generales del clúster ([02-prerequisites.md](02-prerequisites.md)), APISIX
necesita:

- **pid-gijon-core ya desplegado** en el namespace `pid-gijon`: las rutas apuntan a sus Services
  `iot-agent-json`, `orion-ld` y `web-back`.
- **La configuración de Keycloak de una sola vez hecha** ([06-post-install.md](06-post-install.md)),
  para que existan el cliente `laravel-backend` y su secreto.
- **Que `web-back` exponga `POST /api/internal/check-fiware-write-permission`**: es a quien llama la
  autorización por tenant. Recibe `{tenant_name, scope_name}` y la cabecera `Authorization` de quien
  llama, y devuelve `200` para permitir o cualquier otro código para denegar. Si tu compilación de
  `web-back` no tiene ese endpoint interno, el paso de autorización deniega todas las escrituras.
  (La autenticación contra Keycloak sigue funcionando sin él.)
- El **controlador autónomo dirigido por API**, que aporta el subchart `apisix` incluido (chart
  v2.12.5, APISIX 3.9 según su `appVersion`). Basta con ejecutar antes
  `helm dependency update charts/apisix`.
- Un **`public-gateway`** con un listener `https` (el Gateway estándar del repositorio,
  [04-gateway-api.md](04-gateway-api.md)).

## Recorrido de una petición

```
cliente ──▶ public-gateway (Gateway API, TLS) ──▶ apisix-gateway
                                                      │ [1] openid-connect → valida el JWT contra Keycloak
                                                      │ [2] serverless-pre-function → web-back
                                                      │       POST /api/internal/check-fiware-write-permission
                                                      └─[3] proxy → iot-agent-json:4041 | orion-ld:1026
```

El paso `[2]` reenvía la cabecera `Authorization` de quien llama a `web-back`, que extrae del token
la persona usuaria y comprueba si puede escribir en el tenant y el scope solicitados.

## Rutas

| Ruta | Backend | Métodos | Cabeceras obligatorias |
|------|---------|---------|------------------------|
| `/iot/devices`, `/iot/devices/*` | `iot-agent-json:4041` | GET POST PUT DELETE | `Fiware-Service` + `Fiware-ServicePath` |
| `/iot/services`, `/iot/services/*` | `iot-agent-json:4041` | GET POST PUT DELETE | `Fiware-Service` + `Fiware-ServicePath` |
| `/ngsi-ld/v1/*` | `orion-ld:1026` | GET POST PUT PATCH DELETE | `NGSILD-Tenant` |

Las rutas se declaran en `fiware.services`; el `headerType` (`fiware` o `ngsild`) elige las
cabeceras de tenancy. Para añadir un servicio, basta con añadir una entrada — véase
[charts/apisix/README.md](../charts/apisix/README.md).

## Namespace

Despliega el chart en el namespace **`pid-gijon`**, junto a pid-gijon-core. Los backends de un
`ApisixRoute` tienen que vivir en el namespace de la propia ruta (no se admiten backends en otro
namespace), así que ponerlos juntos permite que las rutas apunten directamente a
`iot-agent-json`, `orion-ld` y `web-back`, sin adaptadores `ExternalName`.

## Cómo se expone

APISIX se expone mediante la **Gateway API de Kubernetes**, igual que `pid-gijon-core`
([04-gateway-api.md](04-gateway-api.md)). El chart genera un `HTTPRoute` que se engancha a tu
`public-gateway` existente; **no** crea ningún Gateway. Como corre en `pid-gijon`, la ruta se
engancha con el selector `allowedRoutes` que ya permite ese namespace: **no hay que tocar el
Gateway.**

## Secretos

No se versiona ningún secreto. El chart no renderiza hasta que aportes:

- **`keycloak.clientSecret`** — el **mismo** secreto que usa `web-back` para el cliente
  `laravel-backend` (no crees un cliente nuevo). Se obtiene en la configuración de Keycloak de una
  sola vez, [06-post-install.md](06-post-install.md).
- **La clave de la API de administración de APISIX** (`apisix.apisix.admin.credentials.admin`) —
  la genera por ti `scripts/generate-env.sh` (`APISIX_ADMIN_KEY` en `SECRETS.env`).

El generador conecta ambas, más la URL de descubrimiento y el nombre de host, en
`environments/<entorno>/apisix.values.yaml`. Para GitOps y producción, pon
`keycloak.useExternalSecret: true` y toma las credenciales de Keycloak desde el External Secrets
Operator. Véase [05-secrets.md](05-secrets.md).

## Despliegue

Despliega **después** de `pid-gijon-core` y de la configuración de Keycloak de una sola vez (el
secreto de cliente tiene que existir).

```bash
ENV=prod

# 1. Actívalo: pon APISIX_ENABLED=true en environments/$ENV/config.env y genera:
./scripts/generate-env.sh $ENV          # -> environments/$ENV/apisix.values.yaml

# 2. Descarga el subchart original de apisix:
helm dependency update charts/apisix

# 3. Instala en el namespace pid-gijon:
helm upgrade --install apisix charts/apisix -n pid-gijon \
  -f environments/$ENV/apisix.values.yaml --wait
```

Apunta el DNS de `DOMAIN_APISIX` (por defecto `fiware-secured.<proyecto>.<dominio_base>`) al mismo
punto de entrada que el resto de la plataforma.

## Comprobación

```bash
kubectl get pods -n pid-gijon -l app.kubernetes.io/name=apisix
kubectl get apisixroute -n pid-gijon
kubectl get httproute apisix -n pid-gijon          # Accepted=True / ResolvedRefs=True

# Una petición sin un JWT válido de Keycloak debe rechazarse (401):
curl -s -o /dev/null -w '%{http_code}\n' \
  -H 'Fiware-Service: demo' -H 'Fiware-ServicePath: /' \
  https://fiware-secured.<proyecto>.<dominio_base>/iot/devices
```

## Notas de operación y cosas que conviene comprobar en un clúster real

El chart se genera y se conecta correctamente (`helm lint` y `helm template` limpios; el modo de
despliegue coincide con la receta autónoma oficial de apisix-ingress-controller 2.0). Hay algunos
comportamientos que dependen del clúster en marcha y conviene probar:

- **La autenticación funciona por `openid-connect`** (`bearer_only`): las peticiones sin un JWT
  válido de Keycloak reciben `401`. Esto exige que los pods de APISIX tengan **salida hacia la URL
  de descubrimiento de Keycloak** (`https://<host-kc>/realms/pid-gijon/...`). Si Keycloak solo es
  accesible por dentro, apunta `keycloak.discoveryUrl` a la URL interna del clúster.
- **La autorización por tenant** la impone una `serverless-pre-function` que llama a `web-back` y
  rechaza con `core.response.exit` en la fase `rewrite`. Es la forma fiable de bloquear desde una
  función serverless: un `return` a secas **no** detiene la petición. Comprueba que una escritura a
  un tenant al que la persona usuaria no tiene acceso devuelve el código de denegación del backend.
  Si prefieres un mecanismo de primera clase, el plugin `forward-auth` es la alternativa idiomática,
  pero exige que `web-back` lea el tenant y el scope de cabeceras reenviadas en lugar de un cuerpo
  JSON.
- **Orden de los plugins:** la función de autorización se ejecuta antes que `openid-connect`, pero
  reenvía el token a `web-back`, que lo vuelve a validar, así que un token ausente o inválido
  también se rechaza.
- **Sincronización autónoma:** revisa los registros del controlador y
  `kubectl get apisixroute -n pid-gijon -o yaml` (el `status`) para confirmar que las rutas se han
  sincronizado con el plano de datos.

## Desinstalación

```bash
helm uninstall apisix -n pid-gijon
```

Esto elimina la pasarela y sus rutas; los servicios FIWARE siguen funcionando y vuelven a estar
protegidos directamente por `fiware-manager` y `web-back`.
