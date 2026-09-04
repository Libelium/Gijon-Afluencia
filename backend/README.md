# Backend — PID Gijón

API de gestión y consulta de la plataforma, en **PHP 8.2 / Laravel 10**.

Expone la API REST que consume el front: entidades y dispositivos, series temporales,
cuadros de mando, alarmas, grupos de entidades y preferencias de usuario y de
organización.

> **No es la vía de ingesta de datos.** Las medidas de los dispositivos entran por la
> capa FIWARE (agente IoT → broker de contexto → cola de mensajes → consumidores) y se
> escriben directamente en los almacenes. Este servicio **lee** esos datos para servirlos
> a los usuarios y **escribe** la configuración y los metadatos, que viven en PostgreSQL.

## Estructura

```
Dockerfile                 imagen de ejecución (PHP 8.2 + Apache)
apache2-laravel.conf       vhost :80, cabeceras de seguridad
php.ini                    configuración PHP de producción
docker-compose.yaml        entorno de desarrollo (código montado, recarga en caliente)
docker-compose-image.yaml  ejecución de la imagen construida, sin montaje
libelium_devices_fiware_datamodels/
                           modelos de datos CSV del hardware, copiados a storage/app/CSV
src/                       aplicación Laravel
  app/                     modelos, controladores (API V1), políticas, repositorios, helpers
  app/Authorization/       catálogo único de permisos (AppPermission)
  config/                  configuración; todo parametrizado por variables de entorno
  database/migrations/     esquema principal (189) + realtime/ + device_manager/
  database/seeders/        permisos, preferencias y límites de recursos
  routes/api.php           rutas de la API
  tests/                   PHPUnit (suites Unit y Feature)
```

## Requisitos

- Docker y Docker Compose ≥ 2.17
- **PostgreSQL 15 con PostGIS** — varias migraciones crean columnas de geometría
- Un Keycloak con un realm y un cliente para la API (autenticación por token RS256)

## Configuración

Toda la configuración se lee del entorno. Parte de la plantilla incluida:

```bash
cp src/.env.example src/.env
```

Como mínimo hay que rellenar:

| Variable | Para qué |
| --- | --- |
| `APP_KEY` | clave de aplicación (`php artisan key:generate`) |
| `DB_*` | PostgreSQL/PostGIS principal |
| `DB_REALTIME_*` | base de datos de tiempo real (tabla que alimenta el WebSocket) |
| `DB_DEVICE_MANAGER_DATABASE` | esquema del gestor de dispositivos |
| `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_PUBLIC_KEY` | validación del token de acceso |
| `AETHER_LINK_URL`, `QUEUES_CONSUMER_API_URL`, `COMMANDS_ENDPOINT`, `DEVICE_MANAGER_URL` | servicios vecinos de la plataforma |
| `TRUSTED_PROXIES` | redes de las que se aceptan las cabeceras `X-Forwarded-*` |

Las claves de cifrado (`FILE_ENCRYPTION_KEY`, `GENERIC_ENCRYPTION_KEY`,
`PSEUDONYMIZATION_KEY`, …) se dejan vacías en la plantilla y se generan en la instalación.

Los valores por omisión de la plantilla no requieren Redis ni Elasticsearch
(`CACHE_DRIVER=file`, `QUEUE_CONNECTION=sync`, `SCOUT_DRIVER=null`).

## Construir y ejecutar

```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose build
docker compose up -d          # API en http://localhost:8000
docker compose exec backend composer install   # el montaje de ./src oculta el vendor/ de la imagen
docker compose exec backend php artisan key:generate
```

`docker-compose.yaml` monta `./src` en `/var/www/html`, así que los cambios en el código
se ven sin reconstruir. Ese montaje lo escribe el usuario del contenedor, que **no es root**:
es `www-data`, con uid y gid 1001. Si el usuario del anfitrión tiene otro uid —lo habitual—,
Laravel no podrá escribir `src/storage/logs` ni `src/bootstrap/cache` y la API responderá
error 500 al primer arranque. De ahí el `HOST_UID`/`HOST_GID` del comando de construcción:
`docker-compose.yaml` los pasa como los argumentos `UID`/`GID` de la imagen, que reasignan
el uid y el gid de `www-data`. Sin definirlos se construye con 1001, el valor de despliegue.
Las variables no se llaman `UID`/`GID` porque en bash `UID` es de sólo lectura y la asignación
en línea falla.

Para ejecutar la imagen tal cual se despliega, sin montaje:

```bash
docker compose -f docker-compose-image.yaml up -d
```

## La imagen

Corre como `www-data` (uid 1001) de principio a fin: no vuelve a root en el arranque. Como
Apache sigue escuchando en el puerto 80 —el que esperan los charts y los ficheros de Compose—
y un proceso sin privilegios no puede abrir un puerto por debajo de 1024, el Dockerfile le da
la capacidad al binario:

```dockerfile
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/apache2
```

> **Cuidado al endurecer el `securityContext` de Kubernetes.** Una capacidad de fichero como
> ésa deja de concederse si el contenedor se despliega con `allowPrivilegeEscalation: false`
> (activa `no_new_privs`, que hace que `execve` ignore las capacidades del binario) o con
> `capabilities.drop: ["ALL"]` (vacía el conjunto delimitador). Las dos cosas las exige el
> perfil `restricted` de Pod Security Admission, y ninguna da un aviso: lo que se ve es
> Apache arrancando y muriendo con `(13) Permission denied: could not bind to address
> 0.0.0.0:80`.
>
> **Añadir `capabilities.add: ["NET_BIND_SERVICE"]` no lo arregla.** Kubernetes traduce
> `add` a los conjuntos delimitador, permitido y efectivo del proceso inicial del contenedor,
> nunca al conjunto *ambient*. Como aquí el proceso no es root, cada `execve` de la cadena
> (`docker-php-entrypoint` → `apache2-foreground` → `apache2`) recalcula el conjunto permitido
> y, con las capacidades de fichero anuladas por `no_new_privs` y sin ambient que heredar, se
> queda vacío: Apache muere con el mismo error. La respuesta corta es que la imagen, tal cual,
> es compatible con el perfil `baseline`, no con `restricted`.
>
> La forma de cumplir `restricted` sin tocar la imagen es bajar el umbral de puerto privilegiado
> con el sysctl `net.ipv4.ip_unprivileged_port_start`, que es un *safe sysctl* desde Kubernetes
> 1.22 y que `restricted` no veta; así el 80 deja de necesitar capacidad alguna:
>
> ```yaml
> podSecurityContext:
>   sysctls:
>     - name: net.ipv4.ip_unprivileged_port_start
>       value: "0"
>   seccompProfile: { type: RuntimeDefault }
> containerSecurityContext:
>   runAsNonRoot: true
>   runAsUser: 1001
>   runAsGroup: 1001
>   allowPrivilegeEscalation: false
>   capabilities: { drop: ["ALL"] }
> ```
>
> `runAsUser` y `runAsGroup` no son opcionales ahí: `runAsNonRoot: true` obliga a kubelet a
> comprobar que el usuario de la imagen no es root, y sólo puede hacerlo si es numérico. Por eso
> el `USER` final del Dockerfile es el uid (`$UID`, 1001 por omisión) y no `www-data`; una imagen
> construida con `HOST_UID` distinto —sólo desarrollo— necesita ese mismo uid en `runAsUser`.
>
> A medio plazo lo limpio es mover Apache a un puerto ≥ 1024 (`Listen` de `apache2-laravel.conf`
> y `ports.conf`, `containerPort`/`targetPort` de `webBack` en el chart, y el mapeo `8000:80` de
> los dos ficheros de Compose) y retirar entonces el `setcap`.
>
> El ejemplo de `containerSecurityContext` que documenta `deploy/charts/pid-gijon-core/values.yaml`
> está pensado para los componentes de Python, que escuchan en un puerto alto; copiarlo tal cual
> a este componente tumba el pod.

## Base de datos

```bash
docker compose exec backend php artisan migrate --force
docker compose exec backend php artisan db:seed --class=SyncSeeder   # permisos, preferencias, límites
```

`src/migration.sh` es el arranque no interactivo que se usa en el despliegue: migra las tres
conexiones (principal, realtime y gestor de dispositivos), carga los modelos de datos CSV y
ejecuta los sembradores idempotentes.

## Pruebas

```bash
docker compose exec backend vendor/bin/phpunit
docker compose exec backend vendor/bin/phpunit --testsuite Unit
```

Las pruebas de tipo *Feature* usan `DatabaseTransactions` sobre la base de datos configurada:
necesitan el esquema migrado y los permisos sembrados (`SyncSeeder`).

## Estilo

```bash
docker compose exec backend vendor/bin/pint      # Laravel Pint (PSR-12)
```

---

## Licencia

Desarrollo de Libelium anterior al proyecto PID Gijón, licenciado al Ayuntamiento de Gijón bajo la
[EUPL v1.2](../LICENSE). La titularidad y las licencias de los componentes de terceros están en
[`NOTICE.md`](../NOTICE.md).
