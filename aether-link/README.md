# aether-link

Capa de abstracción sobre el **context broker NGSI (Orion-LD / Orion v2)**, el **IoT Agent** y
el **almacén de series temporales**. Expone una **API REST (FastAPI, Python 3.12)** con la que
el resto de la plataforma consulta y escribe sin conocer qué backend hay detrás: el backend
concreto se elige por configuración y se puede sustituir sin tocar a los clientes.

## Qué expone

Servidor en el puerto `8000` del contenedor (`22000` en la máquina anfitriona).

| Método y ruta | Para qué |
| --- | --- |
| `GET /alive` | Liveness. Devuelve 200 sin consultar ninguna dependencia: sólo dice que el proceso responde. |
| `GET /hchk` | Readiness. Comprueba en paralelo la conectividad de los tres backends configurados; 200 si todos responden, 503 si alguno falla o no contesta en 5 s. |
| `GET /docs` | Swagger UI (sólo si `ENABLE_SWAGGER=true`). |
| `POST /api/v1/time-series/` | Consulta de series temporales (agregaciones, ventanas, paginación). |
| `DELETE /api/v1/time-series/` | Borrado de series. |
| `GET /api/v1/context-broker/dataTypes` | Tipos de entidad presentes en el broker. |
| `GET · POST · DELETE /api/v1/context-broker/entities…` | Alta, consulta, actualización y borrado de entidades NGSI. |
| `GET · PATCH /api/v1/context-broker/*TypeSubscriptions` | Consulta y ajuste de las suscripciones de la plataforma por tipo de entidad. |
| `GET /api/v1/iota/services` | Servicios (grupos de dispositivos) dados de alta en el IoT Agent. |
| `POST /api/v1/iota/provision/service` · `/provision/device` | Aprovisionamiento de servicios y dispositivos. |
| `DELETE /api/v1/iota/devices` | Baja de dispositivos. |

La división entre las dos sondas es deliberada: un `livenessProbe` que dependiera de Orion, del
IoT Agent o de Timescale haría que kubelet matase `aether-link` cada vez que se cae un backend
ajeno. Por eso `livenessProbe` apunta a `/alive` y `readinessProbe` a `/hchk`.

## Backends enchufables

Los backends se cargan en arranque desde `app/core/config/config.py` según tres variables de
entorno. Cada implementación declara sus propios parámetros en un `params_description()`, y el
cargador (`ConfigurableServiceLoader`) los lee del entorno y falla con un mensaje explícito si
falta alguno obligatorio.

| Variable | Valores | Implementación |
| --- | --- | --- |
| `DATA_SOURCE_TYPE` | `timescale` | TimescaleDB propio de la plataforma (opción por defecto) |
| | `orion_ld_timescale` | Timescale gestionado por Orion-LD |
| | `mintaka` | API temporal Mintaka |
| | `quantumleap` | QuantumLeap |
| `CONTEXT_BROKER_TYPE` | `orionld` · `orionv2` | Orion-LD (NGSI-LD) u Orion v2 (NGSI v2) |
| `IOTA_TYPE` | `iotajsonLd` · `iotajsonV2` | IoT Agent JSON, en su variante LD o v2 |

Sólo se activa un backend de cada familia a la vez. Si uno no carga, el contenedor arranca
igualmente y el error queda registrado en el log: así se puede diagnosticar desde `/hchk`.

Para añadir un backend nuevo: implementa la interfaz correspondiente
(`DataSource`, `ContextBrokerProxy` o `IOTAProxy`, todas ellas `ConfigurableService`) y
regístralo en el diccionario `AVAILABLE_SERVICES` de `app/core/config/config.py`.

## Estructura

```
app/
  main.py                    aplicación FastAPI
  api/                       routers HTTP (v1: time-series, context-broker, iota) y /hchk
  core/
    config/                  ajustes, carga de backends y logging
    configurable_service/    interfaz común de todo backend configurable
    context_broker/          proxies Orion-LD y Orion v2 (+ CRUD de entidades y suscripciones)
    iota/                    proxies del IoT Agent y traducción LD ⇄ v2
    time_series/             agregaciones y data sources (Timescale, Orion-LD Timescale,
                             Mintaka, QuantumLeap)
  tests/                     pruebas unitarias (pytest)
gunicorn/                    configuración del servidor WSGI
```

La librería compartida con los modelos de petición y respuesta vive fuera de este directorio,
en [`../pylibs/aether-pylib`](../pylibs/aether-pylib), y se instala en modo editable.

## Configuración

```bash
cp app/.env.example app/.env
```

Edita `app/.env` con los endpoints y credenciales de tu entorno. Las variables obligatorias
dependen del backend elegido; `app/.env.example` documenta las de cada uno.

Ojo con dos detalles:

- `GUNICORN_WORKERS` en `app/.env` no configura el servidor: los data sources de base de datos
  lo usan como **tamaño del pool de conexiones**. Los ajustes reales del servidor se leen de
  `gunicorn/.env` (opcional, ver `gunicorn/.env.example`); sin ese fichero valen los valores
  por defecto de `gunicorn/gunicorn.py`.
  Como el pool de Timescale se abre con `max_overflow=0`, ese valor es además el techo de
  consultas simultáneas de `/api/v1/time-series/` por proceso: los manejadores son síncronos y
  FastAPI los despacha a su pool de hilos, así que las peticiones que pasen del tamaño del pool
  esperan en `pool_timeout` (30 s) y luego fallan con `sqlalchemy.exc.TimeoutError`. Dimensiónalo
  con la concurrencia esperada del endpoint, no con el número de workers de gunicorn.
- `app/.env` no se versiona.

## Construcción y ejecución

Todo corre en contenedor; no hace falta instalar Python en la máquina. Se requiere
**Docker Compose >= 2.17** (el build usa `additional_contexts`).

```bash
docker compose build          # imagen de desarrollo
docker compose up             # levanta el servicio
```

La API queda en `http://localhost:22000` — Swagger en `/docs`, health check en `/hchk`:

```bash
curl http://localhost:22000/hchk
```

El build **no necesita credenciales de ningún índice privado**: la librería compartida se copia
al contexto de build desde `../pylibs` (`additional_contexts`) y se resuelve desde disco.

El `Dockerfile` tiene dos destinos, `dev` y `prod`, idénticos salvo por el uso previsto: en
desarrollo el `docker-compose.yml` monta el código y la librería como volúmenes, de modo que
los cambios se recogen en caliente; para producción se construye `--target prod`, que lleva el
código y la librería dentro de la imagen.

```bash
docker build --target prod --build-context pylibs=../pylibs -t aether-link:prod .
```

## Pruebas

Se ejecutan dentro del contenedor:

```bash
docker compose run --rm --no-deps aether-link pytest ./app/tests/ -q
```

> **`pytest` está declarado en el grupo `test`**, no entre las dependencias de tiempo de
> ejecución. Fuera del contenedor hay que pedirlo de forma explícita, porque el grupo que
> `uv` selecciona por omisión es `dev`: `uv sync --group test && pytest ./app/tests/ -q`.
> Un `uv sync` a secas deja el entorno **sin `pytest`**. Dentro de la imagen sí está,
> porque su `uv sync` usa `--all-groups`.

Las pruebas son unitarias y no necesitan ni base de datos ni broker: los backends se sustituyen
por dobles.

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
