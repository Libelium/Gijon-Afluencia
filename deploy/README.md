# deploy

Todo lo necesario para ejecutar la plataforma sobre Kubernetes —charts de Helm, un generador de
entornos, tres scripts que lo conducen y una batería de verificación posterior a la instalación—
más un fichero de Compose que levanta solo las dependencias de terceros para trabajar en local.

Los charts son **agnósticos de la distribución**: funcionan en k3s, EKS, AKS, GKE y OpenShift. Los
dos scripts `k3s-*.sh` automatizan de principio a fin el camino de k3s en un solo nodo; en
cualquier otra distribución se ejecutan los mismos charts a mano, siguiendo [`docs/`](docs).

| Ruta | Qué es |
|------|--------|
| [`charts/pid-gijon-core`](charts/pid-gijon-core) | El chart de la plataforma: un Deployment y un Service por componente. |
| `charts/{stackgres,mongodb,rabbitmq,minio}` | La capa de datos: PostgreSQL/TimescaleDB, MongoDB, RabbitMQ, almacenamiento de objetos. |
| [`charts/apisix`](charts/apisix) | Pasarela API opcional delante de los endpoints FIWARE (hay que activarla). |
| [`scripts/generate-env.sh`](scripts/generate-env.sh) | Generador de entornos: escribe un fichero de valores por chart, con las credenciales enlazadas de forma coherente. |
| `environments/` | Una carpeta por despliegue. Todo salvo `example/` está excluido de git: contiene secretos reales. |
| [`docs/`](docs) | Documentación de referencia de cada capa, y de cómo sustituirlas por servicios gestionados. |
| [`tests/`](tests) | Batería de verificación que se ejecuta contra una instalación terminada. |
| `build-images.sh` · `k3s-bootstrap.sh` · `k3s-deploy.sh` | Los tres pasos de abajo. |
| `docker-compose.core.yml` · `.env.example` | Las dependencias de terceros, para desarrollo local. |

La release se llama `pid-gijon`, aterriza en el namespace `pid-gijon` y el chart es
`pid-gijon-core`.

---

## Desplegar: tres pasos

### 1. Construir y publicar las imágenes

El script construye siete imágenes. Seis cubren ocho de los diez componentes del chart: los tres
papeles de consumidor (`carrot`, `cb-consumer`, `generic-consumer`) son la misma imagen
`queues-consumer` con un `WORKER_TYPE` distinto. Los otros dos componentes, Orion-LD y el IoT
Agent, son imágenes públicas que el propio chart fija. La séptima imagen es `predictions`, que el
chart no despliega todavía (ver más abajo).

```bash
deploy/build-images.sh registry.example.com/pid-gijon --push
deploy/build-images.sh registry.example.com/pid-gijon --tag v1.0.0 --push   # release fijada
```

Los nombres de repositorio que produce —`aether-link`, `queues-consumer`, `fiware-manager`,
`web-back`, `keycloak`, `frontend` y `predictions`— son exactamente los que el chart espera por
debajo de `global.imageRegistry`. Renombrar uno obliga a cambiar también el chart.

La interfaz web sí forma parte de este repositorio y de este chart: se construye desde
[`frontend`](../frontend) como un componente más y se despliega con los demás. Su particularidad es
que la configuración no se incrusta al compilar: el entrypoint de la imagen escribe un `config.js`
con las variables del contenedor en cada arranque, así que **la misma imagen sirve para cualquier
entorno** y basta con apuntarla a las URL públicas del backend y de Keycloak que estos scripts
configuran.

### 2. Preparar el clúster

```bash
deploy/k3s-bootstrap.sh --domain pid.gijon.example
deploy/k3s-bootstrap.sh --domain pid.gijon.example --dry-run   # imprime, no cambia nada
```

Instala k3s (con su Traefik incorporado desactivado), los CRDs de la Gateway API, Traefik como
controlador de *gateway*, los Gateways `public-gateway` y `tcp-gateway`, un certificado comodín
autofirmado para `*.<dominio>`, el namespace `pid-gijon` y los operadores que necesitan los charts
de datos (StackGres, cert-manager y los dos operadores de RabbitMQ). Es idempotente, y al final se
bloquea hasta que la GatewayClass esté `Accepted` y el Gateway público esté `Programmed`: terminar
en verde con un gateway que nadie ha programado nunca es justo el fallo del que hay que protegerse
aquí.

Dos detalles que resuelve bien, y que a mano es fácil equivocar:

- **Gateway API v1.5.1, solo el canal experimental.** Traefik 3.7 vigila `TLSRoute` y
  `BackendTLSPolicy` en `v1`, y la v1.5.0 es la primera release que sirve `TLSRoute` ahí; con
  cualquier versión anterior los informers del proveedor nunca sincronizan, así que arranca sin
  errores visibles y nunca programa un Gateway. Además, desde la v1.5 la release incluye una
  `ValidatingAdmissionPolicy` (`safe-upgrades`) que rechaza instalar CRDs experimentales encima de
  los estándar, de modo que el canal experimental va solo, no superpuesto al estándar.
- **Los Gateways seleccionan las rutas por la etiqueta del namespace.** Casan
  `kubernetes.io/metadata.name: pid-gijon`, que Kubernetes solo pone automáticamente al crear el
  namespace; el script lo crea y lo etiqueta.

Cuando apuntes el DNS a la dirección del gateway, usa los nombres que imprime el script —`api`,
`kc`, `app` y `fiware` bajo tu dominio—, de un solo nivel para que el certificado comodín los
cubra.

¿Ya tienes un clúster con un controlador de gateway? Sáltate esto y crea los mismos dos Gateways
contra tu propia `GatewayClass`: [`docs/04-gateway-api.md`](docs/04-gateway-api.md) tiene el ejemplo
completo, y [`docs/02-prerequisites.md`](docs/02-prerequisites.md), la tabla de requisitos.

### 3. Desplegar la plataforma

```bash
deploy/k3s-deploy.sh --env prod --domain pid.gijon.example --registry registry.example.com/pid-gijon
```

Se ejecuta por fases, y `--phase <nombre>` ejecuta solo una:

| Fase | Qué hace |
|------|----------|
| `config` | Crea `environments/prod/config.env` y luego genera un fichero de valores por chart. |
| `data` | StackGres, MongoDB, RabbitMQ y (salvo que uses S3) MinIO. |
| `core` | `pid-gijon-core`, con `web-back` desactivado. **Se detiene aquí.** |
| `webback` | Activa `web-back`, que ejecuta las migraciones de la base de datos. |

Revisa `environments/prod/config.env` antes de seguir: las etiquetas de imagen, en particular,
vienen como `latest` por defecto. Los `SECRETS.env` y `keycloak-secrets.env` generados contienen
todas las credenciales que ha creado la instalación; están excluidos de git y su sitio es tu gestor
de contraseñas.

#### Por qué se detiene entre `core` y `webback`

`web-back` valida los JWT contra el realm de Keycloak, así que el realm tiene que existir y hay que
tener dos de sus valores a mano antes de que arranque el backend. La fase `core` levanta Keycloak;
después completas la configuración de una sola vez descrita en
[`docs/06-post-install.md`](docs/06-post-install.md):

1. Copia la **clave pública RS256** del realm en `environments/prod/pid-gijon-core.values.yaml`,
   sustituyendo el marcador `REPLACE_AFTER_KEYCLOAK_SETUP`.
2. Haz lo mismo con el **secreto de cliente de `laravel-backend`**, que es el
   `KC_LARAVEL_BACKEND_SECRET` de `environments/prod/keycloak-secrets.env`: el valor que la
   instalación acaba de sustituir en el realm importado.

Después, ejecuta la última fase:

```bash
deploy/k3s-deploy.sh --env prod --phase webback
```

La imagen de Keycloak necesita dos secretos de cliente (`KC_LARAVEL_BACKEND_SECRET` y
`KC_REALM_MANAGEMENT_SECRET`) y un `BACKEND_URL` en el arranque: la exportación del realm trae
marcadores en lugar de secretos reales, y el entrypoint se niega a arrancar sin ellos.
`k3s-deploy.sh` genera ambos una vez por entorno y los pasa en las fases `core` y `webback`. Si
instalas a mano, ponlos tú en `components.keycloak.secrets`.

### 3 bis. El módulo de predicción

`build-images.sh` construye también la imagen `predictions`, pero **el chart no la despliega**: son
dos tareas programadas que se lanzan aparte, contra la plataforma ya en marcha.

```bash
# Entrenamiento + predicción, a diario
kubectl create cronjob crowd-daily -n pid-gijon \
  --image=<registro>/predictions --schedule="0 3 * * *" \
  -- python scripts/run_daily.py

# Compactación e ingesta del archivo LIDAR
kubectl create cronjob crowd-ote -n pid-gijon \
  --image=<registro>/predictions --schedule="15 * * * *" \
  -- python scripts/run_ote.py
```

Ambas necesitan su propia configuración por entorno: la lee de variables que documenta
[`predictions/.env.example`](../predictions/.env.example), y consumen el mismo almacenamiento de
objetos donde `fiware-manager` archiva la trama LIDAR (`OTE_ARCHIVE_PREFIX`, por defecto
`ote/incoming`). Los detalles del módulo están en su
[`README.md`](../predictions/README.md).

### 4. Verificar

```bash
./tests/run-tests.sh prod
```

Cargas de trabajo del clúster, endpoints públicos, inicio de sesión, el camino completo del dato de
un dispositivo y la persistencia de series temporales: cada fallo viene con el comando que hay que
ejecutar a continuación. Las comprobaciones se ejecutan en orden de dependencia, así que arregla el
*primer* fallo y vuelve a lanzarlas. Las etapas del camino del dato necesitan un dispositivo ya
aprovisionado: se indica con `TEST_DEVICE_SERIAL` y, sin él, se saltan. Detalles en [`tests/README.md`](tests/README.md).

---

## Hacerlo sin los scripts

Los scripts son una envoltura sobre el procedimiento documentado, no un sustituto. A mano, en
cualquier distribución:

```bash
./scripts/generate-env.sh prod          # la 1ª ejecución crea config.env
$EDITOR environments/prod/config.env
./scripts/generate-env.sh prod          # la 2ª genera los ficheros de valores

helm upgrade --install stackgres charts/stackgres -n postgres --create-namespace \
  -f environments/prod/stackgres.values.yaml --wait
# ...lo mismo para mongodb, rabbitmq y minio

helm upgrade --install pid-gijon charts/pid-gijon-core -n pid-gijon --create-namespace \
  -f environments/prod/pid-gijon-core.values.yaml \
  --set components.webBack.enabled=false --wait
# post-instalación de Keycloak, y volver a lanzarlo sin el --set
```

Volver a ejecutar el generador es seguro: reutiliza las contraseñas que ya estén en `SECRETS.env`,
así que puedes subir una etiqueta de imagen y regenerar sin rotar credenciales.

Para apuntar a una base de datos, un broker o un bucket gestionados: define el `EXTERNAL_*`
correspondiente (o `STORAGE_TYPE=s3`) en `config.env` y el generador se salta ese chart y conecta la
plataforma a tu endpoint — [`docs/03-infrastructure.md`](docs/03-infrastructure.md).

---

## La pila de dependencias local

`docker-compose.core.yml` levanta los servicios de terceros que la plataforma necesita: el núcleo
FIWARE y los almacenes de datos, todo imágenes oficiales, nada de código nuestro. No ejecuta la
plataforma en sí; de eso se encarga el fichero de compose de cada componente, contra estos.

```bash
cp deploy/.env.example deploy/.env
# OBLIGATORIO antes de levantar: .env.example ya no trae contrasenas por defecto
# (GDTIS-PT01-SEC-039). Rellena cada valor vacio, p. ej. con `openssl rand -hex 24`.
# Sin ellas `docker compose` se niega a arrancar, que es el comportamiento buscado.
$EDITOR deploy/.env
docker compose -f deploy/docker-compose.core.yml --env-file deploy/.env up -d
docker compose -f deploy/docker-compose.core.yml --env-file deploy/.env ps
```

| Servicio | Puerto en el host | Qué es |
| --- | --- | --- |
| `orion` | 1026 | Orion-LD, el context broker NGSI-LD |
| `iot-agent` | 4041 (norte), 7896 (sur) | IoT Agent JSON |
| `mongo` | 27017 | El almacenamiento propio de Orion-LD |
| `postgres` | 5432 | Modelo de la plataforma — PostGIS, que exigen las migraciones |
| `timescale` | 5433 | Series temporales |
| `rabbitmq` | 5672, 15672 | Colas de trabajo y su interfaz de gestión |
| `minio` | 9000, 9001 | Almacenamiento de objetos para exportaciones y subidas |

Para tirarlo abajo, `down -v` — la `-v` importa: sin ella los volúmenes sobreviven y el siguiente
arranque viene con el estado anterior.

Comprobar que ha levantado:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:1026/version      # 200
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4041/iot/about    # 200
docker exec pid-gijon-timescale psql -U platform -d platformdb_ts \
  -tAc "select extname from pg_extension where extname='timescaledb'"       # timescaledb
```

### Dos versiones fijadas que no son arbitrarias

**`mongo:5.0`.** Orion-LD 1.4.0 sigue usando el driver C++ antiguo, que habla `OP_QUERY`. MongoDB 6
lo eliminó, y Orion aborta al arrancar con `Unsupported OP_QUERY command: listDatabases`. Subir
Mongo obliga a subir también Orion-LD.

**Orion no tiene healthcheck.** Su imagen no trae ni curl ni wget, e invocar el binario `orionld`
como sonda arranca un segundo broker dentro del contenedor. `docker compose ps` lo muestra como
`running` sin estado de salud; compruébalo desde fuera.

### Puertos que chocan

Los puertos del host de aquí no chocan entre sí, pero sí con los servicios: el backend también
quiere el 8000, y el componente Keycloak trae su propio PostgreSQL en el 5432. Levantarlo todo a la
vez exige ordenar antes el mapa de puertos.

---

## Referencia

La documentación de referencia de cada capa está en [`docs/`](docs); el tratamiento de secretos, en
[`SECURITY.md`](SECURITY.md).

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
