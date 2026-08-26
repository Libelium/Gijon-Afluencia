# 1. Visión general

PID Gijón es una plataforma de datos IoT construida sobre el modelo FIWARE / NGSI-LD. El chart
`pid-gijon-core` despliega los **servicios de aplicación**. Los servicios con estado (bases de
datos, broker, almacenamiento de objetos) se despliegan antes, con los charts incluidos o con un
equivalente gestionado — véase [03-infrastructure.md](03-infrastructure.md).

## Componentes

Cada componente es un Deployment y un Service independientes. El nombre del objeto de Kubernetes
es la **clave del componente en kebab-case** (`webBack` → `web-back`), sin prefijo del nombre de
la release, de modo que los componentes se alcanzan entre sí por DNS estable dentro del clúster
(por ejemplo, `http://orion-ld:1026`).

| Componente (clave) | Nombre del servicio | Puertos | Función | Imagen |
|--------------------|---------------------|---------|---------|--------|
| `keycloak` | `keycloak` | 8080, 9000 | Identidad y control de acceso (OIDC). | se construye aquí (`build-images.sh`) |
| `webBack` | `web-back` | 80 | API principal del backend (Laravel). Ejecuta las migraciones al arrancar. | se construye aquí (`build-images.sh`) |
| `frontend` | `frontend` | 8080 | Interfaz web (Vue 3 servido por nginx). Resuelve su configuración al arrancar, así que la misma imagen vale en cualquier entorno. | se construye aquí (`build-images.sh`) |
| `fiwareManager` | `fiware-manager` | 8000 | Archiva la trama cruda de los sensores LIDAR y hace de proxy hacia el IoT Agent. | se construye aquí (`build-images.sh`) |
| `orionLd` | `orion-ld` | 1026, 8000 | Context broker Orion-LD de FIWARE (NGSI-LD). | `quay.io/fiware/orion-ld` |
| `iotAgentJson` | `iot-agent-json` | 7896 (sur), 4041 (norte) | IoT Agent de FIWARE (MQTT/HTTP → NGSI-LD). | `quay.io/fiware/iotagent-json` |
| `aetherLink` | `aether-link` | 8000 | Gestor de suscripciones NGSI-LD y enlace de datos. | se construye aquí (`build-images.sh`) |
| `carrot` | `carrot` | 8001, 8000 | Recibe las notificaciones del broker y las encamina a RabbitMQ. | se construye aquí (`queues-consumer`) |
| `cbConsumer` | `cb-consumer` | 8001, 8000 | Procesa las notificaciones del broker, persiste los datos y alimenta las colas. | se construye aquí (`queues-consumer`) |
| `genericConsumer` | `generic-consumer` | 8001, 8000 | Worker genérico de cola (ETL de afluencia, caché de datos, importación). | se construye aquí (`queues-consumer`) |

Los servicios `cb-consumer`, `generic-consumer` y `carrot` ejecutan **la misma imagen**
`queues-consumer` con un `WORKER_TYPE` distinto.

## Cómo circulan los datos (a grandes rasgos)

```
Dispositivos ──(MQTT/HTTP)──▶ iot-agent-json ──▶ orion-ld (context broker)
                                                       │ notificaciones
                                                       ▼
                                                    carrot ──▶ RabbitMQ
                                                                   │
                                            ┌──────────────────────┴───────────────┐
                                            ▼                                       ▼
                                       cb-consumer                          generic-consumer
                                 (persistencia + series)              (ETL de afluencia / caché)
                                            │                                       │
                                            ▼                                       │
                                 PostgreSQL / TimescaleDB                           │
                                            ▲                                       │
            web-back (API) ◀── usuarios ─┐  │                                       │
                                         └──┴───────────────────────────────────────┘

  cb-consumer replica además el estado de las entidades en la base de datos `realtime`,
  que web-back sirve a través de su API.

  keycloak protege web-back y los consumidores (OIDC).
  aether-link gestiona las suscripciones NGSI-LD entre la plataforma y orion-ld.
```

## Exposición

Los servicios se exponen con la **Gateway API de Kubernetes** (`HTTPRoute` / `TCPRoute`). El chart
engancha las rutas a los Gateways que ya proporcione tu infraestructura; no crea Gateways ni
balanceadores. Véase [04-gateway-api.md](04-gateway-api.md).

Lo habitual es exponer públicamente `web-back` (la API), `frontend` (la interfaz web) y `keycloak`.
`orion-ld`, `carrot` y los consumidores suelen quedarse en la red interna.

## Capacidades opcionales

- **Autoescalado horizontal de pods** (`hpa.enabled`) — necesita metrics-server.
- **Autoescalado por cola con KEDA** para los consumidores — necesita el operador KEDA.
- **Recolección con ServiceMonitor** — necesita los CRDs del Prometheus Operator.
- **Alta disponibilidad activo/pasivo de Orion-LD** mediante un sidecar de elección de líder
  (`leaderElection: true`) — el chart crea entonces la ServiceAccount, el Role/RoleBinding y usa
  un Lease de coordinación; el sidecar se añade en `initContainers`.
- **Pasarela FIWARE con APISIX** (`charts/apisix`) — pasarela opcional que impone autenticación
  JWT de Keycloak y autorización por tenant delante de los endpoints FIWARE. Véase
  [07-apisix.md](07-apisix.md).

Todas vienen desactivadas y se pueden dejar así sin problema.
