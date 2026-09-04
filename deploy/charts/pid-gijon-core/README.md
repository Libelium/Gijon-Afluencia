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
| `components.<nombre>.config.RABBITMQ_CA_FILE_PATH` | `""` | Consumidores con `amqps`: ruta del PEM de la CA del broker dentro del contenedor. Vacía = almacén de confianza del sistema. |
| `components.<nombre>.rabbitmqCaCert` | `""` | Contenido del PEM de esa CA. Con la ruta anterior, el chart emite el Secret `<nombre>-rabbitmq-ca` y lo monta ahí. |
| `components.<nombre>.rabbitmqCaSecret` | `""` | Alternativa: nombre de un Secret que aportas tú con ese PEM. Con la ruta puesta hay que declarar uno de los dos o el chart falla al renderizar. |
| `components.<nombre>.gatewayAPI` | desactivado | Configuración de `HTTPRoute`/`TCPRoute` por componente. |
| `components.<nombre>.{hpa,pdb,serviceMonitor,resources,replicas,...}` | apagado / valores razonables | Ajustes estándar de la carga de trabajo. |
| `KedaAutoscale` | sin definir | Autoescalado opcional por cola con KEDA. |
| `networkPolicy.enabled` | `false` | Segmentación de red por componente, con denegación por defecto. |
| `networkPolicy.egress.enabled` | `false` | Además del ingreso, restringe la salida de cada componente. |
| `networkPolicy.monitoringNamespaces` | `[]` | Namespaces de Prometheus. Vacío con algún `serviceMonitor.enabled`, el chart falla al renderizar. |
| `networkPolicy.kubeletCIDRs` | `[]` | Redes de los nodos, para las sondas del kubelet. |
| `components.<nombre>.networkPolicy` | flujo real | Saltos permitidos hacia y desde el componente. |

## Plantillas

| Fichero | Qué genera | Cuándo |
|---------|------------|--------|
| `deployment.yaml` | Un Deployment por componente, más el Secret de la CA de RabbitMQ | `enabled` |
| `service.yaml` | Service (y headless) | `enabled` y `service` definido |
| `configmap.yaml` | ConfigMap a partir de `config` | `enabled` |
| `secret.yaml` | Secret a partir de `secrets` | `secretsStrategy.type == values` |
| `httproute.yaml` | `HTTPRoute` / `TCPRoute` | `gateway.enabled` + `gatewayAPI.enabled` |
| `hpa.yaml` | HorizontalPodAutoscaler | `hpa.enabled` |
| `pdb.yaml` | PodDisruptionBudget | `pdb.enabled` |
| `servicemonitor.yaml` | ServiceMonitor | `serviceMonitor.enabled` |
| `serviceaccount.yaml`, `rbac.yaml` | ServiceAccount + Role/RoleBinding | `leaderElection` |
| `keda-*.yaml` | ScaledObject + TriggerAuth + Secret de credenciales | `KedaAutoscale` definido |
| `networkpolicy.yaml` | Una NetworkPolicy por componente | `networkPolicy.enabled` |

## Exposición (solo Gateway API)

El chart emite rutas estándar de `gateway.networking.k8s.io` que se enganchan a Gateways
preexistentes; no crea Gateways, ni Ingresses, ni balanceadores de carga de ningún proveedor.
Véase [docs/04-gateway-api.md](../../docs/04-gateway-api.md).

## Segmentación de red

Con `networkPolicy.enabled: true` cada componente recibe su propia `NetworkPolicy`. Al quedar
seleccionado por una política, **todo su tráfico de entrada queda denegado** salvo los saltos que
declara `components.<nombre>.networkPolicy`, derivados del flujo real de la plataforma
(`sensor → iot-agent-json → orion-ld → carrot → RabbitMQ → consumidores → almacenes`, con
`web-back` leyendo los almacenes y `aether-link` por delante del broker, del IoT Agent y de
TimescaleDB).

Viene **desactivada por defecto** porque activarla a ciegas corta tráfico legítimo:

1. Necesita un CNI que implemente `NetworkPolicy` (Calico, Cilium, Antrea). El `kindnet` de kind y
   el flannel a secas la admiten y **no filtran nada**: dan una falsa sensación de seguridad.
2. Actívala primero **solo para el ingreso** (`networkPolicy.enabled: true`) y comprueba que la
   plataforma sigue viva. El egreso es un interruptor aparte
   (`networkPolicy.egress.enabled: true`) porque las bases, el broker, el SMTP y el almacén de
   objetos son externos al chart: hay que declarar antes
   `networkPolicy.egress.infrastructureNamespaces` (si están en el clúster) o
   `networkPolicy.egress.externalCIDRs` (si están fuera). El DNS del clúster se abre solo.
3. Rellena `networkPolicy.gatewayNamespaces` con el namespace de los Gateways y
   `networkPolicy.monitoringNamespaces` con el de Prometheus, o el tráfico de entrada público y el
   scrapeo de métricas se quedan fuera. Para que eso no ocurra en silencio, **el chart falla al
   renderizar si activas la política junto a algún `serviceMonitor.enabled` y
   `monitoringNamespaces` está vacío**; si tu Prometheus no encaja en un namespace (scrapeo desde
   el nodo, por ejemplo), abre el salto a mano en `extraIngress` y el chart deja de exigirlo.
4. Si tu CNI somete a política las sondas del kubelet, sus `livenessProbe` dejan de responder en
   **todos** los componentes —y antes que en ninguno en `cb-consumer` y `generic-consumer`, que
   solo consumen de RabbitMQ y no reciben ninguna otra regla de entrada—. No hay selector portable
   para el kubelet: declara las redes de los **nodos** en `networkPolicy.kubeletCIDRs`, que abre la
   entrada desde ellas en todos los componentes. No pongas ahí el CIDR de pods del CNI (en k3s,
   `10.42.0.0/16`): abriría todos los puertos de todos los componentes a cualquier pod del clúster
   y anularía la segmentación en silencio. Para un salto suelto sigue estando
   `components.<nombre>.networkPolicy.extraIngress`.
5. La tabla de saltos debe ser simétrica: si `X` declara `egressToComponents: [Y]`, `Y` tiene que
   declarar `X` en su `ingressFromComponents`. Con el egreso activado el tráfico solo pasa si lo
   permiten los dos extremos, así que una entrada suelta corta la llamada.

## Secretos

Este chart no incluye ninguna credencial: todos los valores secretos son marcadores. Súmalos en el
despliegue (estrategia `values`) o por fuera (estrategia `external`). Véase
[docs/05-secrets.md](../../docs/05-secrets.md).

Con `RABBITMQ_SECURITY: amqps` los consumidores (`carrot`, `cbConsumer`, `genericConsumer`) validan
el certificado del broker y abortan el arranque si no encuentran una CA. Si lo firma una CA pública
basta con dejar `RABBITMQ_CA_FILE_PATH` vacío. Si lo firma una CA propia, indica la ruta del PEM
dentro del contenedor en `config.RABBITMQ_CA_FILE_PATH` (`scripts/generate-env.sh` la propaga desde
`EXTERNAL_RABBITMQ_CA_FILE_PATH`) y **además una de estas dos**: el PEM en `rabbitmqCaCert` —el
chart emite el Secret `<componente>-rabbitmq-ca` y lo monta en esa ruta— o el nombre del Secret que
aportas tú en `rabbitmqCaSecret`. Con la ruta puesta y ninguna de las dos, **el chart falla al
renderizar**, en vez de montar un Secret que nadie crea y dejar el fallo para el
`FailedMount` del pod. Sin ruta no se monta nada (despliegue `amqp`).

Con `scripts/generate-env.sh` el PEM va siempre por fuera: el values del entorno se regenera en
cada ejecución, así que un `rabbitmqCaCert` añadido a mano ahí se pierde. Por eso el script rellena
`rabbitmqCaSecret` con `carrot-rabbitmq-ca`, `cb-consumer-rabbitmq-ca` y
`generic-consumer-rabbitmq-ca` en cuanto hay ruta: crea tú esos tres Secrets, con la clave igual al
nombre de fichero de `RABBITMQ_CA_FILE_PATH`. El script te lo recuerda al generar el entorno.

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
