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

Las claves de cifrado (`FILE_ENCRYPTION_KEY`, `GENERIC_ENCRYPTION_KEY`,
`PSEUDONYMIZATION_KEY`, …) se dejan vacías en la plantilla y se generan en la instalación.

Los valores por omisión de la plantilla no requieren Redis ni Elasticsearch
(`CACHE_DRIVER=file`, `QUEUE_CONNECTION=sync`, `SCOUT_DRIVER=null`).

## Construir y ejecutar

```bash
docker compose build
docker compose up -d          # API en http://localhost:8000
docker compose exec backend composer install   # el montaje de ./src oculta el vendor/ de la imagen
docker compose exec backend php artisan key:generate
```

`docker-compose.yaml` monta `./src` en `/var/www/html`, así que los cambios en el código
se ven sin reconstruir. Para ejecutar la imagen tal cual se despliega, sin montaje:

```bash
docker compose -f docker-compose-image.yaml up -d
```

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
