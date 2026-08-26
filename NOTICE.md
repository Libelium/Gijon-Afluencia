# Titularidad y licencias

Este documento acompaña a [`LICENSE`](LICENSE) y detalla, para cada parte del repositorio, quién
la desarrolló y bajo qué licencia se entrega.

## Aviso de copyright

    Copyright © 2026 Ayuntamiento de Gijón
    Copyright © 2026 Libelium Comunicaciones Distribuidas, S.L.

    Licensed under the EUPL

La EUPL v1.2 pide que el licenciante coloque la leyenda «Licensed under the EUPL» inmediatamente
después del aviso de copyright de la obra. Ese es el aviso de arriba, repetido en la cabecera de
[`LICENSE`](LICENSE); el reparto entre ambos titulares es el que detallan las secciones 1 y 2.

## Resumen

Salvo lo que se indica más abajo, el software de este repositorio es **desarrollo previo de
Libelium**, anterior e independiente del proyecto PID Gijón, o bien **componente de terceros** con
licencia propia. Libelium lo licencia al Ayuntamiento de Gijón bajo la **EUPL v1.2**.

Lo desarrollado **específicamente para el proyecto** es de **titularidad del Ayuntamiento de
Gijón**: el módulo de predicción de afluencia y fusión de sensores (LIDAR + Smart Spot), en
[`predictions`](predictions), y la **interfaz web**, en [`frontend`](frontend).

### Autoría y titularidad no son lo mismo

Conviene distinguirlas, porque los manifiestos de los paquetes declaran una y este documento
declara la otra:

- El campo **`authors`** de `pyproject.toml`, `composer.json` y `package.json` indica **quién
  escribió** el código. Es Libelium en los componentes de la sección 1 y el propio proyecto en los
  de la sección 2.
- La **titularidad** —de quién son los derechos sobre esta entrega— la establecen
  [`LICENSE`](LICENSE) y este documento: corresponde al **Ayuntamiento de Gijón**, por cesión bajo
  EUPL v1.2 en lo previo de Libelium y en propiedad en lo escrito para el proyecto.

El campo `license` de los nueve manifiestos del repositorio —los seis `pyproject.toml`, el
`composer.json` y los dos `package.json`— declara `EUPL-1.2`, en coherencia con el `LICENSE` del
repositorio.

## 1. Desarrollo previo de Libelium

Escrito por Libelium antes del proyecto y en uso en otros despliegues. Se entrega bajo EUPL v1.2.

| Carpeta | Qué es |
| --- | --- |
| [`aether-link`](aether-link) | Capa de abstracción sobre el context broker, el IoT Agent y el almacén de series temporales |
| [`queues-consumer`](queues-consumer) | Flota de workers: sincronización, tiempo real, ETL de análisis, caché e importación |
| [`fiware-manager`](fiware-manager) | Puente de ingesta para las fuentes que no hablan FIWARE de forma nativa: archivado de la trama LIDAR y proxy hacia el IoT Agent |
| [`backend`](backend) | API de gestión: entidades y dispositivos, series temporales, cuadros de mando, alarmas y preferencias |
| [`keycloak`](keycloak) | Configuración de identidad —realm, tema de acceso y arranque— **escrita sobre** Keycloak. El producto en sí es de terceros y no se incluye: ver la sección 3 |
| [`pylibs/aether-pylib`](pylibs/aether-pylib) | Biblioteca Python compartida |
| [`deploy`](deploy) | Charts de Helm, scripts de construcción y despliegue, y pila local de dependencias |

La adaptación de estos componentes a las necesidades del proyecto (configuración, modelos de
datos, cuadros de mando y la ingesta de los sensores desplegados en la ciudad) se entrega en las
mismas condiciones que el resto: EUPL v1.2, sin restricción de uso, modificación ni redistribución.

## 2. Desarrollado para el proyecto

Escrito expresamente para el proyecto PID Gijón. Es **propiedad del Ayuntamiento de Gijón** y se
entrega bajo la misma EUPL v1.2 que el resto.

### 2.1. Predicción de afluencia y fusión de sensores

Fusión LIDAR + Smart Spot, clasificación de visitantes, modelo de predicción de aforo y detección
de anomalías.

Está en [`predictions`](predictions), con su propio código, pruebas y documentación. Consume el
resto de la plataforma a través de sus interfaces públicas: lee y escribe medidas por la API de
[`aether-link`](aether-link) y publica sus resultados como entidades del context broker, de modo
que ambas piezas se despliegan y se actualizan por separado.

### 2.2. Interfaz web

Visualizador de datos de sensores urbanos: cuadros de mando, análisis y mapa. Está en
[`frontend`](frontend).

Su código es **original y escrito para este proyecto**. La única entrada externa ha sido la
especificación HTTP de la API con la que se integra: se implementó un cliente contra ese contrato,
sin reutilizar código, hojas de estilo, plantillas de interfaz ni recursos gráficos de ningún
producto comercial o propietario. Consume la API de gestión descrita en
[`openapi-gestion.yaml`](openapi-gestion.yaml) y se autentica contra Keycloak.

Sus dependencias son paquetes públicos de npm, incorporados **sin modificar**. El listado completo
con versiones y licencias está en
[`frontend/THIRD-PARTY-LICENSES.md`](frontend/THIRD-PARTY-LICENSES.md), y los recursos gráficos
propios, en [`frontend/ASSETS.md`](frontend/ASSETS.md).

## 3. Componentes de terceros

Cada uno conserva su propia licencia, que prevalece sobre la de este repositorio. Hay dos
situaciones distintas, y conviene no confundirlas:

- **Se despliegan sin modificar.** La plataforma los configura y depende de ellos, pero no los
  incluye: se descargan de sus registros públicos al construir o al desplegar. Es el caso de todos
  los de la tabla salvo el siguiente.
- **Se construye una imagen derivada.** La imagen de Keycloak **se construye en este repositorio**
  (`keycloak/Dockerfile`) partiendo de `quay.io/keycloak/keycloak:25.0` y añadiéndole la extensión
  de segundo factor por correo que se indica más abajo. El resultado es obra derivada de software
  Apache-2.0 y se redistribuye conservando esa licencia y sus avisos.

| Componente | Versión | Procedencia |
| --- | --- | --- |
| Keycloak | 25.0 | `quay.io/keycloak/keycloak` — Apache-2.0 |
| Orion-LD (context broker) | 1.4.0 | `quay.io/fiware/orion-ld` — FIWARE, AGPL-3.0 |
| IoT Agent JSON | 3.3.0 | `quay.io/fiware/iotagent-json` — FIWARE, AGPL-3.0 |
| MongoDB | 5.0 | `mongo` — SSPL-1.0 |
| PostgreSQL + PostGIS | 15 / 3.4 | `postgis/postgis` — PostgreSQL: PostgreSQL License · PostGIS: GPL-2.0-or-later |
| TimescaleDB | 2.14.2 | `timescale/timescaledb` — Apache-2.0 y Timescale License |
| StackGres (operador PostgreSQL) | chart en [`deploy/charts`](deploy/charts) | AGPL-3.0 |
| RabbitMQ | 3.13 | `rabbitmq` — MPL-2.0 |
| MinIO | RELEASE.2024-06-13 | `minio/minio` — AGPL-3.0 |
| Apache APISIX | chart 2.12.5 | Apache-2.0 |
| keycloak-2fa-email-authenticator | commit `7dbcdf7` | [mesutpiskin/keycloak-2fa-email-authenticator](https://github.com/mesutpiskin/keycloak-2fa-email-authenticator) — Apache-2.0. Se compila con Maven y **se empaqueta dentro de la imagen de Keycloak**, que lleva copia de su licencia en `/opt/keycloak/licences/` |

A esto se añaden las imágenes base de los contenedores (`python`, `php`, `maven` y
`registry.access.redhat.com/ubi9`, esta última solo como etapa de construcción de la imagen de
Keycloak) y los árboles de dependencias de cada componente, que se resuelven en la construcción
desde los índices públicos de paquetes (PyPI y Packagist) y cuyas licencias son las que declara
cada paquete. El inventario completo, con versión y licencia de cada uno, está en
[`sbom.json`](sbom.json).

Las licencias de esta tabla se indican a título informativo; la referencia es la que publique cada
proyecto en la versión que se despliegue.

Dos precisiones sobre ese inventario, porque son las dos que suele levantar una revisión de
licencias:

- **Los componentes con copyleft fuerte de la tabla —AGPL-3.0, SSPL-1.0, GPL-2.0-or-later— se
  despliegan como servicios independientes, sin modificar y sin enlazarse con el código de la
  plataforma.** La obligación que arrastran es conservar sus avisos, no extender su licencia a esta
  obra. Es el caso de Orion-LD, el IoT Agent, MinIO, StackGres, MongoDB y la extensión PostGIS de
  la imagen `postgis/postgis`.
- **`sbom.json` sobredeclara un paquete.** `nvidia-nccl-cu12`
  (`LicenseRef-NVIDIA-Proprietary`) aparece en el inventario porque el fichero de bloqueo de
  [`predictions`](predictions) lo arrastra como dependencia de `xgboost`, pero su `Dockerfile` lo
  desinstala justo después de instalar el proyecto: **no viaja en ninguna imagen que se despliegue**
  y no se redistribuye.

## 4. Atribuciones obligatorias

Además de conservar los avisos de licencia de cada componente, hay dos atribuciones que **no deben
retirarse** porque las exigen los términos de uso de sus proveedores:

**Cartografía — OpenStreetMap.** La vista de mapa de la interfaz web consume por defecto teselas de
OpenStreetMap. Los datos son © colaboradores de OpenStreetMap, bajo Open Data Commons Open Database
License (ODbL) v1.0; las teselas se publican bajo Creative Commons Attribution-ShareAlike 2.0
(CC BY-SA 2.0). La leyenda «© colaboradores de OpenStreetMap» se muestra de forma permanente en el
control de atribución del mapa. Si un despliegue sustituye el proveedor de teselas
(`VITE_MAP_TILES_URL`), debe sustituir también el texto de atribución
(`VITE_MAP_TILES_ATTRIBUTION`) por el que exija el nuevo proveedor.

- Datos: <https://www.openstreetmap.org/copyright> · ODbL 1.0:
  <https://opendatacommons.org/licenses/odbl/1-0/>
- Teselas: <https://operations.osmfoundation.org/policies/tiles/>

**Smart Data Models.** La plataforma modela los datos según NGSI-LD (ETSI GS CIM 009) y los Smart
Data Models, publicados bajo Creative Commons Attribution 4.0 (CC BY 4.0) —
<https://smartdatamodels.org>.

## 5. Marcas

*Libelium* y *Smart Spot* son marcas de Libelium Comunicaciones Distribuidas, S.L. La licencia de
este código no otorga derecho sobre ellas. FIWARE, Keycloak, PostgreSQL y el resto de nombres
citados son marcas de sus respectivos titulares.
