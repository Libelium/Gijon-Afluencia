# PID Gijón

Plataforma de Integración de Datos del Ayuntamiento de Gijón: recoge las medidas que envían los
sensores desplegados en la ciudad, las normaliza contra un núcleo FIWARE, las almacena, ejecuta
sobre ellas los procesos de análisis y predicción, y las devuelve a través de una API.

Este repositorio contiene el código de la plataforma, una carpeta por componente, incluida la
interfaz web.

---

## Componentes

| Carpeta | Qué hace | Tecnología |
| --- | --- | --- |
| [`aether-link`](aether-link) | Capa de abstracción sobre el context broker, el IoT Agent y el almacén de series temporales | Python 3.12 · FastAPI |
| [`queues-consumer`](queues-consumer) | Flota de workers: sincronización, tiempo real, ETL de análisis, caché e importación | Python 3.10 · Celery |
| [`fiware-manager`](fiware-manager) | Puente para las fuentes que no hablan FIWARE de forma nativa, incluida la ingesta de los sensores LIDAR | Python 3.11 · FastAPI |
| [`backend`](backend) | API de gestión: entidades y dispositivos, series temporales, cuadros de mando, alarmas y preferencias | PHP 8.2 · Laravel 10 |
| [`predictions`](predictions) | Predicción de afluencia y fusión LIDAR + Smart Spot | Python 3.10 · XGBoost |
| [`frontend`](frontend) | Interfaz web: cuadros de mando, análisis y mapa | Vue 3 · Vuetify · Vite |
| [`keycloak`](keycloak) | Identidad y autenticación: realm, tema de acceso y arranque | Keycloak 25 |
| [`pylibs/aether-pylib`](pylibs/aether-pylib) | Biblioteca Python compartida | Python |
| [`deploy`](deploy) | Charts de Helm, scripts de construcción y despliegue, y pila local de dependencias | Helm · Bash |

Orion-LD, el IoT Agent, MongoDB, PostgreSQL/TimescaleDB, RabbitMQ y MinIO son componentes de
código abierto de terceros. La plataforma los configura y depende de ellos; los charts de
[`deploy`](deploy) los despliegan junto a ella. Sus versiones y licencias están en
[`NOTICE.md`](NOTICE.md).

## Cómo circulan los datos

El dato **no entra por la API de gestión**. Entra por el núcleo FIWARE:

```
sensor → IoT Agent → Orion-LD → suscripción → RabbitMQ
       → consumidor de contexto (crea la entidad, guarda la serie temporal
         y la fila de tiempo real)
       → consumidor genérico (ETL de análisis, caché de resultados, importación)
       → PostgreSQL / TimescaleDB / MongoDB
```

El backend Laravel es la ruta de **lectura y gestión** para las personas usuarias, no la de
ingesta. Los tres roles de consumidor son la misma imagen con distinta variable `WORKER_TYPE`.

## Desplegar

Tres pasos: construir las imágenes, preparar el clúster y desplegar. El detalle está en
[`deploy/README.md`](deploy/README.md).

```bash
deploy/build-images.sh <registro> --push
deploy/k3s-bootstrap.sh --domain <dominio>
deploy/k3s-deploy.sh --env prod --domain <dominio> --registry <registro>
```

Se despliega sobre cualquier distribución de Kubernetes. Los scripts automatizan el camino de
k3s; en el resto se aplican los mismos charts.

## Trabajar sobre un componente

Cada componente arranca con Docker Compose y se construye desde índices de paquetes públicos:
no hace falta cuenta en ningún proveedor cloud ni registro privado.

```bash
cd aether-link
cp app/.env.example app/.env      # y editar
docker compose up
```

Los puertos, la ubicación del fichero de entorno y el comando de pruebas de cada componente
están en su propio `README.md`.

## Licencia y titularidad

El código se distribuye bajo la **Licencia Pública de la Unión Europea (EUPL) v1.2**; el texto
completo está en [`LICENSE`](LICENSE).

Todo lo que contiene este repositorio es **desarrollo previo de Libelium** —anterior e
independiente del proyecto— o bien **componente de terceros** con licencia propia, salvo
[`predictions`](predictions).

Es de **titularidad del Ayuntamiento de Gijón** lo escrito para este proyecto: el **módulo de
predicción de afluencia y fusión de sensores** (LIDAR + Smart Spot), en
[`predictions`](predictions), y la **interfaz web**, en [`frontend`](frontend).

El desglose por componente, con las versiones y las licencias de los componentes de terceros, está
en [`NOTICE.md`](NOTICE.md).
