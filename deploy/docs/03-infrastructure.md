# 3. Servicios de infraestructura (bases de datos, broker, almacenamiento)

pid-gijon-core depende de PostgreSQL/TimescaleDB, MongoDB, RabbitMQ y almacenamiento de objetos
compatible con S3. Este repositorio incluye un chart para cada uno, de modo que puedes levantarlos
con un solo comando — pero **cualquiera de ellos puede ser un servicio gestionado externo** (véanse
los avisos «↔ Externo»).

El generador (`scripts/generate-env.sh`) escribe en `environments/<nombre>/` un fichero de valores
listo para usar por chart, con las credenciales ya casadas con las que pone en
`pid-gijon-core.values.yaml`. Los comandos de abajo usan esos ficheros.

> Los nombres de host que se muestran son los valores por defecto dentro del clúster a los que
> apunta el generador. Sobrescríbelos en `config.env` (`EXTERNAL_*`) para apuntar a servicios
> gestionados.

---

## 3.1 PostgreSQL + TimescaleDB — `charts/stackgres`

Usa el **operador StackGres**. Un `SGCluster` más los scripts de inicialización que crean los roles
y las bases de datos que la plataforma necesita.

```bash
helm upgrade --install stackgres charts/stackgres -n postgres --create-namespace \
  -f environments/<nombre>/stackgres.values.yaml --wait
```

### La inicialización de la base de datos es automática

**No** hay que ejecutar ningún `psql` ni `kubectl apply` para sembrar la base de datos: el chart
engancha la inicialización al propio clúster y StackGres la aplica cuando este arranca por primera
vez. El chart genera tres piezas:

| Recurso | Nombre | Función |
|---------|--------|---------|
| `Secret` | `pid-gijon-postgres-init-scripts` | el SQL ordenado (roles, bases de datos, extensiones) |
| `SGScript` | `pid-gijon-init` | referencia cada clave SQL del Secret, en orden |
| `SGCluster` | `pid-gijon-postgres` | ejecuta `pid-gijon-init` mediante `managedSql` en el arranque |

Cómo se comporta:

- **Se ejecuta una vez, sola.** StackGres ejecuta los scripts la primera vez que el clúster
  arranca. Cada entrada lleva una `version`; StackGres registra lo que ya ha aplicado, así que
  volver a lanzar `helm upgrade` **no** vuelve a ejecutar los scripts que no han cambiado.
- **Ordenada e idempotente.** Los roles se crean con guardas `IF NOT EXISTS` y van numerados
  `001…020`, de modo que las dependencias (rol → base de datos → extensión) se aplican en orden.
- **Falla de forma ruidosa.** Tanto `managedSql.continueOnSGScriptError` como el `continueOnError`
  del script están en `false`, así que un script roto bloquea la disponibilidad del clúster en vez
  de dejar una base de datos a medio inicializar. Si el clúster nunca llega a `Ready`, mira
  `kubectl describe sgcluster pid-gijon-postgres -n postgres`.
- **Ningún secreto en git.** Las contraseñas de los roles vienen del generador
  (`scripts/generate-env.sh` → `environments/<nombre>/stackgres.values.yaml`); el `values.yaml` del
  propio chart las trae vacías y **falla al renderizar** si falta la contraseña de algún rol
  obligatorio.

El SQL en sí se edita en `charts/stackgres/templates/init-scripts-secret.yaml` (al añadir un
script, añade también su entrada en `script.yaml`).

**Bases de datos y roles que se crean** (las contraseñas vienen del generador):

| Base de datos | Rol | La usa |
|---------------|-----|--------|
| `platformdb` | `platformdb` | web-back, fiware-manager, consumidores, aether-link |
| `platform_ts` (TimescaleDB) | `platformdb` | series temporales (aether-link, consumidores) |
| `keycloak` | `keycloak` | keycloak |
| `realtime` | `realtime` | consumidores (escriben el estado) y web-back (lo sirve) |
| `airflow` | `airflow` | complemento opcional; solo se crea si defines `initScripts.passwords.airflow` |

- DNS del servicio: `pid-gijon-postgres.postgres.svc.cluster.local:5432`
- Para escalar a alta disponibilidad o ajustar recursos, edita `stackgres.values.yaml`
  (`cluster.instances`, `instanceProfile`, `postgresqlConf`).
- Los roles y bases `airflow` y `geoportal` son opcionales y vienen **desactivados**: solo se
  inicializan si defines su contraseña en `initScripts.passwords` (por ejemplo, con `--set`).

> **↔ Externo (RDS, Cloud SQL, Timescale Cloud):** define `EXTERNAL_POSTGRES_HOST` (y `_PORT`) en
> `config.env`. El generador se salta entonces este chart y apunta pid-gijon-core a tu endpoint.
> Tendrás que crear tú las bases de datos y los roles `platformdb`, `platform_ts`, `keycloak` y
> `realtime` (replicando el SQL de `charts/stackgres/templates/init-scripts-secret.yaml`).

---

## 3.2 MongoDB — `charts/mongodb`

Un `StatefulSet` independiente llamado `mongodb` (sin operador). Da soporte a los componentes
FIWARE.

```bash
helm upgrade --install mongodb charts/mongodb -n mongodb --create-namespace \
  -f environments/<nombre>/mongodb.values.yaml --wait
```

- Usuario `fiware-mongo-user` (base de datos de autenticación `admin`); las bases `orion` e
  `iotajson` las crean automáticamente los componentes al usarlas por primera vez.
- El generador apunta los componentes FIWARE al nombre DNS estable por pod
  `mongodb-0.mongo-headless.mongodb.svc.cluster.local:27017`. El servicio ClusterIP
  `mongo-svc.mongodb.svc.cluster.local:27017` resuelve a esa misma instancia única.

> **⚠️ Orion-LD se autentica con usuario y contraseña, no con una URI única.** Orion-LD se
> configura con los campos fragmentados `ORIONLD_MONGO_HOST` / `ORIONLD_MONGO_PORT` (en `config`)
> más `ORIONLD_MONGO_USER` / `ORIONLD_MONGO_PASSWORD` (en el secreto), con
> `ORIONLD_MONGO_AUTH_SOURCE: "authSource=admin"` — fíjate en que el valor es el fragmento de
> consulta completo, no solo el nombre de la base de autenticación. Esto replica las instalaciones
> on-premise en producción. **No** uses la forma de URI única (`-dbURI` / `ORIONLD_MONGO_URI`): ha
> demostrado no ser fiable. El generador emite los campos fragmentados automáticamente.

> **↔ Externo (Atlas, DocumentDB):** define `EXTERNAL_MONGO_HOST`/`_PORT` en `config.env`. Crea tú
> el usuario (lectura y escritura sobre `orion` e `iotajson`).

---

## 3.3 RabbitMQ — `charts/rabbitmq`

Usa **dos** operadores de RabbitMQ: el **Cluster Operator** (`RabbitmqCluster`) y el **Messaging
Topology Operator** (`User` / `Vhost` / `Permission`). El chart crea el clúster, el vhost
`pid-gijon` y un usuario de aplicación con permiso sobre él, de modo que ambos operadores (y
cert-manager, que necesita el Topology Operator) deben estar instalados antes, o la instalación
falla con `no matches for kind "Vhost" … ensure CRDs are installed first`. Los comandos de
instalación están en [02-prerequisites.md](02-prerequisites.md#operadores-de-rabbitmq).

```bash
helm upgrade --install rabbitmq charts/rabbitmq -n rabbitmq --create-namespace \
  -f environments/<nombre>/rabbitmq.values.yaml --wait
```

- vhost `pid-gijon` (coincide con el `RABBITMQ_VHOST` de pid-gijon-core)
- DNS del servicio: `pid-gijon.rabbitmq.svc.cluster.local:5672`

> **↔ Externo (CloudAMQP, Amazon MQ):** define `EXTERNAL_RABBITMQ_HOST`/`_PORT`/`_SECURITY`
> (`amqps` para TLS) en `config.env`. Crea tú el vhost y el usuario.

---

## 3.4 Almacenamiento de objetos

El `STORAGE_TYPE` de pid-gijon-core elige el modo (se define en `config.env`).

### `local` — MinIO incluido (`charts/minio`)

Envuelve el chart oficial `minio/minio`, así que primero hay que construir la dependencia:

```bash
helm dependency update charts/minio
helm upgrade --install minio charts/minio -n minio --create-namespace \
  -f environments/<nombre>/minio.values.yaml --wait
```

- Bucket `pid-gijon-storage`, con un par de claves de acceso y secreta acotado a él (generadas).
- DNS del servicio: `minio.minio.svc.cluster.local:9000` (consola en `:9001`).

### `s3` — servicio externo compatible con S3

Define `STORAGE_TYPE=s3` más `S3_BUCKET`, `S3_REGION`, opcionalmente `S3_ENDPOINT` (si no es AWS) y
`S3_ACCESS_KEY`/`S3_SECRET_KEY` en `config.env`. El generador se salta MinIO y conecta esas
credenciales a pid-gijon-core. No hay chart que desplegar.

---

## 3.5 Opcional: broker MQTT

Solo hace falta para dispositivos que publiquen por MQTT. Despliega cualquier broker MQTT (por
ejemplo, Mosquitto) y define `iotAgentJson.config.IOTA_MQTT_HOST` más los secretos
`IOTA_MQTT_USERNAME`/`IOTA_MQTT_PASSWORD` en tus valores de pid-gijon-core.

---

## Endpoints por defecto dentro del clúster

| Servicio | DNS | Puerto |
|----------|-----|--------|
| PostgreSQL / TimescaleDB | `pid-gijon-postgres.postgres.svc.cluster.local` | 5432 |
| MongoDB | `mongodb-0.mongo-headless.mongodb.svc.cluster.local` (o `mongo-svc.mongodb.svc.cluster.local`) | 27017 |
| RabbitMQ | `pid-gijon.rabbitmq.svc.cluster.local` | 5672 |
| MinIO | `minio.minio.svc.cluster.local` | 9000 |

Cuando todos estén en marcha y en estado `Ready`, despliega pid-gijon-core: es la fase `core` del
[README.md](../README.md) de despliegue.
