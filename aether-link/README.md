# aether-link

Capa de abstracción sobre el **context broker NGSI (Orion-LD / Orion v2)**, el **IoT Agent** y
el **almacén de series temporales**. Expone una **API REST (FastAPI, Python 3.12)** con la que
el resto de la plataforma consulta y escribe sin conocer qué backend hay detrás: el backend
concreto se elige por configuración y se puede sustituir sin tocar a los clientes.

## Qué expone

Servidor en el puerto `8000` del contenedor (`22000` en la máquina anfitriona).

| Método y ruta | Para qué |
| --- | --- |
| `GET /hchk` | Health check. Comprueba la conectividad de los tres backends configurados. |
| `GET /docs` | Swagger UI (sólo si `ENABLE_SWAGGER=true`). |
| `POST /api/v1/time-series/` | Consulta de series temporales (agregaciones, ventanas, paginación). |
| `POST /api/v1/time-series/hash` | Hash sha256 determinista de lo que devolvería la consulta anterior, calculado en base de datos. |
| `DELETE /api/v1/time-series/` | Borrado de series. |
| `GET /api/v1/context-broker/dataTypes` | Tipos de entidad presentes en el broker. |
| `GET · POST · DELETE /api/v1/context-broker/entities…` | Alta, consulta, actualización y borrado de entidades NGSI. |
| `GET · PATCH /api/v1/context-broker/*TypeSubscriptions` | Consulta y ajuste de las suscripciones de la plataforma por tipo de entidad. |
| `GET /api/v1/iota/services` | Servicios (grupos de dispositivos) dados de alta en el IoT Agent. |
| `POST /api/v1/iota/provision/service` · `/provision/device` | Aprovisionamiento de servicios y dispositivos. |
| `DELETE /api/v1/iota/devices` | Baja de dispositivos. |

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

> **Nota de subsanación (COD-102).** `pytest` ya no es una dependencia de tiempo de
> ejecución: se ha movido al grupo `test` del `pyproject.toml`, para que no viaje en la
> imagen de producción.
>
> - Para que el comando de arriba siga funcionando, el `Dockerfile` debe sincronizar
>   también ese grupo, igual que ya hace `queues-consumer`:
>   `uv sync --locked --no-install-project --all-groups --no-cache`.
> - En local, el grupo hay que pedirlo de forma explícita, porque el grupo que `uv`
>   selecciona por defecto es `dev`, no `test`:
>   `uv sync --group test && pytest ./app/tests/ -q`.
>   Un `uv sync` a secas deja el entorno **sin `pytest`**. Esa es exactamente la causa
>   raíz de FUN-019 en `queues-consumer`, donde se confundió con una dependencia sin
>   declarar; allí se ha fijado `default-groups = ["test"]`, que aquí no se puede usar
>   porque el `Dockerfile` no selecciona grupos y volvería a meter `pytest` en la imagen.

Las pruebas son unitarias y no necesitan ni base de datos ni broker: los backends se sustituyen
por dobles.

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
