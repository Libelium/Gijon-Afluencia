# Registro de cambios

Todos los cambios reseñables de la plataforma se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[semántico](https://semver.org/lang/es/). Cada componente lleva además su propia versión en su
manifiesto (`pyproject.toml`, `composer.json`); la versión de esta página es la del conjunto.

## [1.0.0] — Entrega inicial

Primera versión de la Plataforma de Integración de Datos ajustada al alcance del proyecto: ingesta
de sensores LIDAR y Smart Spot, análisis de afluencia, entidades, series temporales, cuadros de
mando, alarmas y preferencias.

### Añadido

- **Interfaz web** ([`frontend`](frontend)): visualizador de datos de sensores urbanos con cuadros de
  mando, análisis y mapa. Aplicación Vue 3 servida por nginx, con la configuración resuelta en
  arranque, de modo que la misma imagen vale para cualquier entorno. Se despliega como un componente
  más del chart. Es de titularidad municipal, igual que el módulo de predicción.

- **Documentación de la API** en formato OpenAPI 3, generada a partir de las rutas reales del
  servicio: [`openapi-gestion.yaml`](openapi-gestion.yaml) para la API de gestión (124 rutas, 164
  operaciones) y [`openapi-ingesta.yaml`](openapi-ingesta.yaml) para la de ingesta (4 rutas, 5
  operaciones).
- **Colecciones Postman** listas para importar, derivadas de las especificaciones anteriores, en
  [`postman/`](postman).
- **Inventario de componentes de terceros (SBOM)** en formato CycloneDX 1.5
  ([`sbom.json`](sbom.json)): 424 componentes con su versión, identificador `purl` y licencia
  declarada, incluidas las imágenes de infraestructura que despliega la plataforma.
- **Ficheros de bloqueo de dependencias**: `uv.lock` en los seis proyectos Python y `package-lock.json` en la interfaz web, de modo que cada
  construcción es reproducible y la cadena de dependencias queda auditable.
- **Guía de contribución** ([`CONTRIBUTING.md`](CONTRIBUTING.md)) y este registro de cambios, como
  documentación viva del proyecto.

### Cambiado

- **El análisis de afluencia se ejecuta para todas las organizaciones del despliegue**, sin
  condicionantes de licencia ni de contrato. Los cinco procesos de `queues-consumer` que lo calculan
  recorren el conjunto completo de organizaciones.
- **Toda la documentación del repositorio está en castellano**: 43 documentos, incluidas la guía de
  despliegue, la referencia de infraestructura, secretos, Gateway API y pasarela API, y la
  documentación funcional de los procesos ETL de afluencia y del consumidor de colas.
- **Nomenclatura propia del proyecto** en las tareas, las colas y el *exchange* de RabbitMQ, que
  pasan al espacio de nombres `platform.*`, junto con las variables de entorno que se derivan del
  nombre de cola. El cambio es coherente en `backend`, `predictions`, `queues-consumer` y el chart
  de despliegue.
- **Licencia y autoría declaradas de forma uniforme**: los nueve manifiestos del repositorio
  (`composer.json`, los dos `package.json` y los seis `pyproject.toml`) indican `EUPL-1.2` y nombran en
  `authors` a quien escribió cada componente, en coherencia con el reparto del
  [`NOTICE.md`](NOTICE.md). La titularidad de la entrega la establecen [`LICENSE`](LICENSE) y ese
  mismo documento.
- **Construcción reproducible** de las imágenes Python: se instalan desde el fichero de bloqueo
  (`uv sync --locked`), que pasa a ser obligatorio en la construcción.

### Eliminado

- **Funcionalidad ajena al objeto del contrato**, para reducir la superficie mantenida y auditable:
  informes y exportaciones, conectores de entrada y salida, incidencias, espacios de trabajo,
  gestión de roles y permisos, personalizador, módulos de inteligencia artificial, simulación
  meteorológica y la API pública v1. La API de gestión queda en 157 rutas y 27 controladores.
- **Modelo comercial de la plataforma**: catálogo de contratos y planes, agrupaciones de permisos
  por contrato, límites de recursos por plan y los módulos de facturación, reventa e integración con
  servicios de terceros asociados. La plataforma se entrega sin condicionantes de licencia sobre su
  funcionalidad.
- **Vías de ingesta no utilizadas en este despliegue**: LoRaWAN y su integración con ChirpStack,
  datalogger ONE, puente MQTT y sonda Cesva. El servicio de ingesta queda acotado a los dos caminos
  del proyecto —archivado de la trama LIDAR y proxy hacia el IoT Agent— y a 1.286 líneas de código.
- **Código sin uso** resultante de lo anterior: 115 clases huérfanas del backend (modelos,
  políticas, repositorios, recursos y validadores) y 81 permisos de aplicación no referenciados.

### Corregido

- **Consolidación de la superficie de la API de gestión**: todas las rutas publicadas resuelven
  contra un controlador existente. Se retiraron nueve rutas heredadas que no lo hacían, entre ellas
  las variantes `create` y `edit` que `Route::resource` genera para formularios HTML y que una API
  no utiliza.
- **Documentación de despliegue al día** con la configuración real del servicio de ingesta: los
  secretos y las variables de entorno documentados coinciden con los que el servicio necesita.
