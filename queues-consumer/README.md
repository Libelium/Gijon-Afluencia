# queues-consumer

Flota de **workers Celery** de la plataforma. Consume los mensajes que llegan por **RabbitMQ** y
ejecuta con ellos el trabajo asíncrono: sincronización de las notificaciones del context broker,
escritura de series temporales y de la tabla de tiempo real, importación de datos y los procesos
ETL de la solución de análisis, con su caché de resultados.

**Una sola imagen, varios roles.** El proceso no se especializa por código sino por la variable de
entorno `WORKER_TYPE`: cada valor determina a qué colas se suscribe el worker y qué módulos de
tareas carga. Así se despliegan tantos *deployments* como haga falta (uno dedicado a la ingesta,
otro a las tareas genéricas, otro a la analítica…) a partir del mismo artefacto.

- Stack: **Python 3.10 · Celery 5 · FastAPI** (API lateral) · SQLAlchemy · RabbitMQ.
- Puertos en local: `20430` → API lateral (`/hchk`), `20431` → métricas Prometheus.
- Servicio de Compose: `queues-consumer`.

---

## Arrancar en local

Requisitos: **Docker Compose ≥ 2.17** (el `Dockerfile` usa `additional_contexts`). No hace falta
ningún registro privado ni credenciales de proveedor cloud: todas las dependencias salen de PyPI y
la biblioteca compartida se resuelve como ruta local a [`../pylibs/aether-pylib`](../pylibs/aether-pylib).

```bash
cp .env.example .env      # y rellenar credenciales y URLs
docker compose up         # --build la primera vez
```

Comprobación rápida:

```bash
curl localhost:20430/hchk       # -> "OK"
curl localhost:20431/metrics    # métricas Prometheus
```

Necesita, como mínimo, un RabbitMQ alcanzable y las dos bases PostgreSQL (principal y de tiempo
real). La pila de dependencias para desarrollo se levanta desde [`../deploy`](../deploy).

## Pruebas

Se ejecutan **dentro del contenedor**, con pytest:

```bash
docker compose run --rm --no-deps queues-consumer pytest ./app/tests/ -q
```

## Construir la imagen

```bash
docker build --target prod -t queues-consumer:local --build-context pylibs=../pylibs .
```

El `Dockerfile` tiene tres etapas: `base` (entorno virtual y dependencias), `dev` (la que usa
Compose, con el código montado para recarga en caliente) y `prod`.

---

## Tipos de worker

`WORKER_TYPE` (por defecto `universal`) selecciona colas y módulos de tareas. La definición está en
[`app/config/queue_worker_type.py`](app/config/queue_worker_type.py) y las colas en
[`app/config/queues.py`](app/config/queues.py).

**Workers de dominio** — cada uno atiende un único dominio:

| Valor | Colas que consume |
| --- | --- |
| `sync` | Notificaciones del context broker, series temporales, tiempo real, suscripciones |
| `alarms` | Evaluación de alarmas: condiciones de umbral y de inactividad |
| `data` | Importación de datos |
| `crowd` | ETL de la solución de análisis: visitantes, clasificación, flujos, visitantes únicos |
| `data_cache` | Caché de los resultados de la analítica |

**Workers agregados:**

| Valor | Qué consume |
| --- | --- |
| `universal` | Todas las colas y todos los módulos de tareas (valor por defecto) |
| `universal_on_premise` | Todas salvo las no necesarias en instalación propia |
| `core` | `sync` + `data` |
| `custom` | Las colas listadas en `CUSTOM_QUEUES`, en `app/config/queues.py` |

**Workers de infraestructura:**

| Valor | Qué consume |
| --- | --- |
| `cb_processor` | Sólo la cola de notificaciones del context broker |
| `generic_processor` | Todas las colas menos esa |
| `dlq_recovery` | Modo de recuperación de la *dead letter queue*: no consume colas al arrancar |

En producción se despliegan normalmente dos: `cb_processor` absorbe la ingesta —que es el volumen
alto y debe poder escalar por separado— y `generic_processor` se ocupa de todo lo demás.
`dlq_recovery` se lanza puntualmente, como *job*, para reprocesar los mensajes fallidos.

## Colas

Todas cuelgan del *exchange* directo `platform`, con nombre igual a su *routing key*.

```
platform.sync.cb_notification            platform.crowd.process_visitors[_all]
platform.sync.new_cb_subscription        platform.crowd.classification[_all]
platform.sync.timeseries                 platform.crowd.flows_municipality[_all]
platform.sync.realtime                   platform.crowd.unique_visitors
platform.sync.auto_subscription_sync     platform.crowd.unique_visitors_all_job
platform.data.importation                platform.data-cache.crowd[_all]
platform.alarms.entity_data_check        platform.alarms.check_inactivity
```

La prioridad y el *timeout* de cada cola se ajustan por entorno con
`QUEUE_TASK_CONFIG_<COLA>_<PARÁMETRO>` (ver `.env.example`).

## Cómo entra el trabajo

```
Orion-LD --(suscripción)--> RabbitMQ --> worker `cb_processor`
      -> crea/actualiza la entidad, guarda la serie temporal y la fila de tiempo real
      -> encola el trabajo derivado --> worker `generic_processor`
```

El punto de entrada del camino de ingesta es `EntitySync`
([`app/jobs/sync/entity_sync.py`](app/jobs/sync/entity_sync.py)): traduce la notificación NGSI a un
modelo interno y ejecuta sobre ella una lista de *observers*. Añadir comportamiento a la ingesta es
añadir un observer, no tocar el flujo.

## Alarmas

El motor de alarmas vive en [`app/jobs/alarms/`](app/jobs/alarms) y atiende dos colas:

- `platform.alarms.entity_data_check` — evalúa las **condiciones de umbral** de las alarmas que
  afectan a la entidad que acaba de reportar. Los valores que la notificación no trae (otras
  medidas u otras entidades de la misma alarma) se leen de la serie temporal por el aether-link.
- `platform.alarms.check_inactivity` — repasa las **condiciones de inactividad** comparando el
  último dato de cada entidad con su tiempo de espera. La lanza celery beat cada
  `INACTIVITY_ALARM_CHECK_INTERVAL` segundos, porque nadie notifica que un dato *no* ha llegado.

Las condiciones de una alarma se combinan con su función lógica (`AND`, `OR`, `XOR`). Cuando el
estado cambia, se registra el cambio, se publica el histórico en el IoT Agent (modelo de datos
`PlatformAlarm`, opcional) y se ejecutan las acciones ligadas a esa transición (`up` o `down`).

El motor ejecuta los **seis canales de acción** que la API de gestión permite configurar:

| Canal | `actionable_type` | Qué hace |
| --- | --- | --- |
| Telegram | `action_telegram` | Mensaje al chat que enlazó la persona usuaria |
| SMS | `action_sms` | Mensaje corto por AWS SNS |
| WhatsApp | `action_whatsapp` | Mensaje por la API de Meta |
| Correo | `action_email` | Correo por SMTP (`MAIL_*`), con el asunto y el cuerpo configurados |
| Aviso HTTP | `action_http_push` | Petición a un servicio externo con el estado de la alarma |
| Comando a la entidad | `action_entity_command` | Escribe los comandos configurados como atributos `Command` en el context broker a través del aether-link; de ahí el IoT Agent los entrega al `fiware-manager`, que los guarda pendientes hasta que el dispositivo vuelve a reportar. El comando enviado se marca como pendiente en la base de tiempo real, igual que el lanzado a mano, para que la interfaz lo muestre |

Cada canal está apagado hasta que se rellena su configuración (ver `.env.example`). Si falta, la
alarma se evalúa y se registra igual: el aviso se salta con una advertencia en el log, nunca
interrumpe la evaluación.

El **aviso HTTP** llama a una URL que escribe quien configura la alarma, así que sólo se envía a los
destinos declarados en `HTTP_PUSH_ALLOWED_DESTINATIONS` (hosts o prefijos de URL, separados por
comas). **La lista vacía —el valor por omisión— no envía nada.** Un host permite ese host y sus
subdominios; un prefijo de URL se compara por partes (esquema, host, puerto y tramo de ruta), nunca
como prefijo de cadena, y se rechazan las URL con credenciales. Además se rechazan los destinos que
resuelven a una dirección privada o de bucle local, no se siguen redirecciones (un 30x no relaya la
petición a otro host) y la espera está acotada por `HTTP_PUSH_REQUEST_TIMEOUT`.

También se puede encolar trabajo por HTTP contra la API lateral:

```bash
curl -X POST localhost:20430/publish -H 'Content-Type: application/json' \
  -d '{"task": "platform.data.importation_job", "params": {...}}'
```

Las tareas periódicas las programa **celery beat** contra la propia base de datos
(`sqlalchemy_celery_beat`), y se activan con `LAUNCH_CELERY_SCHEDULER=true`.

## Estructura

```
app/
  config/     ajustes, colas, tipos de worker, app de Celery
  tasks/      tareas Celery: la fina capa que recibe el mensaje y delega
  jobs/       la lógica de cada trabajo (sync, crowd, data, data_cache, tiempo real, …)
  etls/       procesos ETL por extract / transform / load
  models/     modelos SQLAlchemy y sus CRUD
  schemas/    esquemas Pydantic de entrada y salida
  helpers/    clientes de servicios externos (aether-link, IoT Agent, Keycloak, tiempo real)
  metrics/    colectores Prometheus
  db/         sesiones SQLAlchemy (principal, tiempo real, series temporales)
  services/   procesos que no son tareas Celery (recuperación de la DLQ)
  utils/      traductores NGSI, cliente RabbitMQ, correo
  tests/      pytest
docs/         notas de detalle de algunos procesos (ETL, DLQ, sincronización)
```

Para añadir un trabajo nuevo: cola en `app/config/queues.py`, tarea en `app/tasks/`, lógica en
`app/jobs/`, y alta del par en los mapas de `app/config/queue_worker_type.py`.

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example). Las imprescindibles:

| Variable | Para qué |
| --- | --- |
| `WORKER_TYPE` | Rol del worker (tabla anterior) |
| `QUEUE_CONSUMER_WORKERS`, `WORKER_CONCURRENCY` | Número de procesos y concurrencia por proceso |
| `RABBITMQ_*` | Conexión al broker (`RABBITMQ_SECURITY`: `amqp` o `amqps`) |
| `DB_*` | Base de datos principal |
| `DB_REALTIME_*` | Base de datos de tiempo real |
| `TS_DB_*`, `TIMESERIES_TYPE` | TimescaleDB (`TIMESERIES_TYPE`: `timescale` o `none`) |
| `AWS_S3_*` / `LOCAL_*`, `STORAGE_TYPE` | Almacén de objetos: S3 o endpoint compatible (MinIO) |
| `AETHER_LINK_URL`, `IOTA_URL` | Servicios de la plataforma que consulta el worker |

## Observabilidad

- `GET /hchk` en el puerto `20430`.
- Métricas Prometheus en el `20431`. En modo *prefork* hay varios procesos, así que
  `PROMETHEUS_MULTIPROC_DIR` debe apuntar a un directorio escribible y compartido.
- Trazas opcionales a Sentry con `SENTRY_DSN`.
- Recuperación de la cola de mensajes fallidos: ver
  [`docs/dlq/dead_letter_queue_recovery.md`](docs/dlq/dead_letter_queue_recovery.md).

## Documentación de detalle

En [`docs/`](docs) están descritos paso a paso los procesos menos evidentes:

| Documento | Contenido |
| --- | --- |
| [`docs/sync/device_probe_sync.md`](docs/sync/device_probe_sync.md) | Sincronización dispositivo ↔ sondas en cada notificación entrante |
| [`docs/etls/analytics/`](docs/etls/analytics) | ETL de analítica: clasificación de visitantes, flujos, visitantes únicos |
| [`docs/etls/data_cache/`](docs/etls/data_cache) | Volcado de resultados de analítica al almacén de objetos |
| [`docs/dlq/`](docs/dlq) | Recuperación de la cola de mensajes fallidos |

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
