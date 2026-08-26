# Chart de Helm pid-gijon-core

Chart de Helm agnóstico de la infraestructura que despliega los **componentes de aplicación de la
plataforma PID Gijón** sobre cualquier distribución de Kubernetes. Los servicios con estado
(PostgreSQL, MongoDB, RabbitMQ, almacenamiento de objetos, el controlador de Gateway) se
aprovisionan aparte y son requisitos previos.

Este README es la referencia del chart. Para la guía de despliegue de principio a fin, véanse el
[README.md](../../README.md) de despliegue y la carpeta [`docs/`](../../docs).

## En resumen

```bash
# Desde la raíz del repositorio: genera un entorno y despliega con su fichero de valores.
./scripts/generate-env.sh prod                    # edita environments/prod/config.env y vuelve a ejecutarlo
helm upgrade --install pid-gijon charts/pid-gijon-core -n pid-gijon --create-namespace \
  -f environments/prod/pid-gijon-core.values.yaml
```

El procedimiento completo por fases está en el [README.md](../../README.md) de despliegue, y la
configuración de una sola vez en
[docs/06-post-install.md](../../docs/06-post-install.md).

## Qué despliega

Un paraguas de Deployments y Services independientes, uno por cada entrada de `components`. Los
nombres de objeto son la clave del componente en kebab-case (`webBack` → `web-back`), **sin**
prefijo del nombre de la release, de modo que los componentes se alcanzan entre sí por DNS estable
dentro del clúster (`http://orion-ld:1026`, `http://web-back`…). Los diez componentes son
`keycloak`, `webBack`, `frontend`, `fiwareManager`, `orionLd`, `iotAgentJson`, `aetherLink`,
`carrot`, `cbConsumer` y `genericConsumer`. Véase
[docs/01-overview.md](../../docs/01-overview.md).

## Valores principales

| Ruta | Por defecto | Para qué |
|------|-------------|----------|
| `global.imageRegistry` | `""` | Registro que se antepone a los repositorios de imagen privados. |
| `global.imagePullSecrets` | `[]` | Secrets de descarga que se añaden a todos los pods. |
| `global.environment` | `pid-gijon` | Valor de la etiqueta `environment` en todos los recursos. |
| `gateway.enabled` | `true` | Generar las rutas de Gateway API. |
| `gateway.namespace` | `gateway` | Namespace de los Gateways padre. |
| `gateway.httpsSectionName` | `https` | Sección del listener HTTPS que usan las rutas `httpsOnly`. |
| `secretsStrategy.type` | `values` | `values` (el chart genera los Secrets) o `external` (los aportas tú). |
| `components.<nombre>.enabled` | `true` | Activa o desactiva un componente. |
| `components.<nombre>.image.{registry,repository,tag,pullPolicy}` | — | La imagen. `registry` cae por defecto en `global.imageRegistry`. |
| `components.<nombre>.config` | — | Se convierte en un ConfigMap (`<nombre>-config`), inyectado con `envFrom`. |
| `components.<nombre>.secrets` | `{}` | Se convierte en un Secret (`<nombre>-secret`) con la estrategia `values`. |
| `components.<nombre>.gatewayAPI` | desactivado | Configuración de `HTTPRoute`/`TCPRoute` por componente. |
| `components.<nombre>.{hpa,pdb,serviceMonitor,resources,replicas,...}` | apagado / valores razonables | Ajustes estándar de la carga de trabajo. |
| `KedaAutoscale` | sin definir | Autoescalado opcional por cola con KEDA. |

## Plantillas

| Fichero | Qué genera | Cuándo |
|---------|------------|--------|
| `deployment.yaml` | Un Deployment por componente | `enabled` |
| `service.yaml` | Service (y headless) | `enabled` y `service` definido |
| `configmap.yaml` | ConfigMap a partir de `config` | `enabled` |
| `secret.yaml` | Secret a partir de `secrets` | `secretsStrategy.type == values` |
| `httproute.yaml` | `HTTPRoute` / `TCPRoute` | `gateway.enabled` + `gatewayAPI.enabled` |
| `hpa.yaml` | HorizontalPodAutoscaler | `hpa.enabled` |
| `pdb.yaml` | PodDisruptionBudget | `pdb.enabled` |
| `servicemonitor.yaml` | ServiceMonitor | `serviceMonitor.enabled` |
| `serviceaccount.yaml`, `rbac.yaml` | ServiceAccount + Role/RoleBinding | `leaderElection` |
| `keda-*.yaml` | ScaledObject + TriggerAuth + Secret de credenciales | `KedaAutoscale` definido |

## Exposición (solo Gateway API)

El chart emite rutas estándar de `gateway.networking.k8s.io` que se enganchan a Gateways
preexistentes; no crea Gateways, ni Ingresses, ni balanceadores de carga de ningún proveedor.
Véase [docs/04-gateway-api.md](../../docs/04-gateway-api.md).

## Secretos

Este chart no incluye ninguna credencial: todos los valores secretos son marcadores. Súmalos en el
despliegue (estrategia `values`) o por fuera (estrategia `external`). Véase
[docs/05-secrets.md](../../docs/05-secrets.md).

## Integraciones opcionales

- **HPA** (`components.<nombre>.hpa.enabled`) — necesita metrics-server.
- **KEDA** (`KedaAutoscale`) — necesita el operador KEDA; aporta las credenciales de RabbitMQ en
  tus propios valores (el Secret de credenciales viene vacío).
- **ServiceMonitor** (`components.<nombre>.serviceMonitor.enabled`) — necesita los CRDs del
  Prometheus Operator.
- **Alta disponibilidad activo/pasivo de Orion-LD** (`components.orionLd.leaderElection: true`) —
  el chart añade la ServiceAccount y el RBAC; el sidecar de elección de líder lo añades tú en
  `initContainers`.

## Validar en local

```bash
helm lint charts/pid-gijon-core
helm template pid-gijon charts/pid-gijon-core -n pid-gijon -f environments/prod/pid-gijon-core.values.yaml
```
