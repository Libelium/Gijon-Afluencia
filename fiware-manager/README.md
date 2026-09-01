# FIWARE Manager

Puente de ingesta para fuentes de datos que **no hablan FIWARE de forma nativa**.
Cubre dos caminos: el **archivado de la trama cruda de los sensores LIDAR**, y un
**proxy hacia el IoT Agent** que además resuelve la entrega de comandos al
dispositivo, que el camino nativo de FIWARE no hace de forma fiable.

Servicio FastAPI (Python 3.11) servido con gunicorn.

## Qué expone

Todas las rutas cuelgan de `/api/v1` salvo el health check.

| Ruta | Método | Para qué |
| --- | --- | --- |
| `/hchk` | GET | Health check (200). |
| `/api/v1/ote/{device_id}` | POST | **Ingesta de sensores LIDAR** (Object Tracking Events). |
| `/api/v1/command-proxy/{resource}` | POST, PUT | **Medidas de los dispositivos HTTP** hacia el IoT Agent; con `getCmd=1` devuelve además los comandos pendientes. |
| `/api/v1/notify/command/{serial}` | POST | El IoT Agent entrega aquí un comando; se encola como pendiente hasta que el dispositivo vuelve a reportar. |

El par `command-proxy` + `notify/command` es el ciclo de comandos: el
aprovisionamiento registra `/notify/command/{id}` como endpoint del dispositivo en el
IoT Agent, el comando se guarda pendiente en MongoDB, y el dispositivo lo recoge en la
respuesta de su siguiente envío de medidas. Sin comandos pendientes, la respuesta
es `204`.

## Ingesta LIDAR (módulo `ote`)

Es el camino crítico de este componente y tiene un diseño deliberado:

- El sensor considera **fallo cualquier respuesta que no sea 2xx** y reintenta, así que
  el endpoint responde `200` de inmediato y encola el cuerpo sin parsearlo. Un error de
  parseo nunca puede convertirse en un no-2xx ni en una trama duplicada.
- Un hilo de fondo (`app/core/ote/raw_ote_archiver.py`) acumula las tramas por
  dispositivo y las escribe **verbatim**, en lotes NDJSON comprimidos con gzip, sobre
  almacenamiento de objetos (`app/core/ote/storage.py`): **S3** o **MinIO** según
  `STORAGE_TYPE`. Se arranca y se para en el `lifespan` de `app/main.py`.
- Las ventanas están **acotadas por tamaño**, no solo por tiempo
  (`OTE_FLUSH_MAX_BYTES`, `OTE_MAX_BUFFER_BYTES`): con 36 sensores una ventana de media
  hora llegaba a 1,5 GB y desbordaba la memoria del proceso.
- El endpoint es público, así que se protege con un secreto compartido
  (`OTE_WEBHOOK_TOKEN`) que se acepta en la cabecera `X-OTE-Token` o en el parámetro
  `?t=` para emisores que solo permiten configurar la URL.
- `device_id` viene de la URL y acaba en la clave del objeto: se sanea para que una
  ruta manipulada no pueda escapar del prefijo.

## Estructura

```
app/
  main.py                     app FastAPI, middlewares, lifespan
  api/v1/routes/api.py        registro de routers
  api/v1/routes/*.py          un router por camino de entrada
  core/ote/                   ingesta LIDAR: buffer + archivado a S3/MinIO
  core/commands/              comandos pendientes por dispositivo (MongoDB)
  core/iota/                  traducción de atributos para el IoT Agent
  core/parser/                aplanado de payloads JSON anidados
  core/db/                    conexión a MongoDB
  core/config/                settings leídos del entorno
  tests/                      pytest
config/
  .env.example                plantilla de configuración
  gunicorn.py                 configuración de gunicorn (carga config/.env)
```

El único almacén propio es **MongoDB** (comandos pendientes). El servicio no habla con
PostgreSQL: la ingesta no necesita consultar el inventario de dispositivos.

## Configuración

El servicio se configura **solo por entorno**. `config/gunicorn.py` hace
`load_dotenv("config/.env")`, por lo que el fichero **tiene que estar en
`config/.env`**: cualquier `.env` en otra ruta se ignora en silencio.

```sh
cp config/.env.example config/.env
# y rellenar los valores
```

Bloques principales: MongoDB (`MONGO_DB_*`), IoT Agent (`IOTA_SOUTH_SERVICE`),
gunicorn (`GUNICORN_*`) y archivo LIDAR (`OTE_*`, `STORAGE_TYPE`,
`AWS_S3_*` / `LOCAL_*`).

Todos los valores numéricos (`HTTP_TIMEOUT`, `OTE_*`) se parsean como enteros: no se
pueden dejar en blanco.

## Construir y ejecutar

Requiere **Docker Compose ≥ 2.17**. El servicio de Compose se llama `fiware-manager`.

```sh
docker compose build          # primera vez, o tras tocar pyproject.toml
docker compose up             # levanta en http://localhost:30006
```

El código se monta en el contenedor (`.:/code`), así que los cambios se recargan sin
reconstruir. La imagen se construye con `uv` desde `pyproject.toml`; el destino `dev`
es el de desarrollo y `prod` el de despliegue.

Comprobaciones rápidas:

```sh
curl http://localhost:30006/hchk        # -> {"status":"OK"}
```

La documentación OpenAPI (`/docs`, `/redoc`) solo se publica si `ENABLE_SWAGGER=true`;
fuera de desarrollo debe quedar desactivada.

## Pruebas

pytest, dentro del contenedor:

```sh
docker compose run --rm --no-deps fiware-manager pytest ./app/tests/ -q
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

Los tests viven en `app/tests/`, agrupados por módulo (`ote/`, `parser/`, `iota/`).
No hay linter ni formateador configurado: seguir el
estilo del código de alrededor.

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
