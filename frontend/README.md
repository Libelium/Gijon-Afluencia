# PID-GIJÓN

**Visualizador de datos de sensores urbanos.** Consulta el estado de la red de sensores de la
ciudad, explora su histórico, analiza la evolución de las medidas en paneles de *business
intelligence* y vigila las alarmas configuradas sobre esos datos.

Aplicación web desarrollada **para el Ayuntamiento de Gijón** y publicada como **software libre**
bajo la licencia **EUPL-1.2**.

---

## Índice

- [Qué es](#qué-es)
- [Capturas](#capturas)
- [Funcionalidades](#funcionalidades)
- [Arquitectura](#arquitectura)
- [Estándares abiertos](#estándares-abiertos)
- [Requisitos](#requisitos)
- [Arranque](#arranque)
- [Variables de entorno](#variables-de-entorno)
- [Construcción y despliegue](#construcción-y-despliegue)
- [Documentación](#documentación)
- [Procedencia del código](#procedencia-del-código)
- [Licencia](#licencia)
- [Titularidad](#titularidad)

---

## Qué es

Una ciudad instrumentada produce muchos más datos de los que se pueden mirar de uno en uno. Hay
sensores de calidad del aire, de ruido, de tráfico, de consumo de agua o energía, de llenado de
contenedores, de ocupación del espacio público. Cada uno publica sus medidas cada pocos minutos.
Al cabo de un año, un único sensor ha generado cientos de miles de lecturas.

PID-GIJÓN es la herramienta con la que esos datos se convierten en algo que se puede leer:

- **Un inventario consultable** de lo que hay desplegado y de si sigue enviando datos.
- **Un mapa** que sitúa cada sensor y permite abrir cualquiera de ellos.
- **Paneles de análisis** que agregan el histórico y muestran tendencias, comparaciones y
  cifras de resumen.
- **Alarmas** que avisan cuando una medida se sale de lo esperado, con su histórico de disparos.

Está pensada para dos públicos con necesidades distintas: quien gestiona un servicio municipal y
necesita saber qué está pasando **ahora**, y quien analiza la evolución de un indicador y necesita
**series largas bien agregadas**.

No es un cuadro de mando cerrado: los paneles se definen sobre los datos disponibles, y la
aplicación se limita a leerlos y representarlos con fidelidad.

---

## Funcionalidades

### Entidades

El inventario de la red. Una **entidad** es cada elemento del que se reciben datos: una estación de
calidad del aire, un contador, un punto de conteo, un depósito.

- Listado paginado en servidor, con búsqueda por nombre y filtro por **modelo de datos**.
- Marca temporal del **último dato recibido** de cada entidad, resuelta para toda la página en una
  sola llamada: es el indicador rápido de si un sensor ha dejado de hablar.
- Ficha de detalle con su identificador, su modelo de datos, su ubicación y **sus medidas con el
  último valor y su unidad**.
- Serie temporal de cualquier medida, con selector de rango.

Solo se muestran las medidas que son propiedades observadas: las relaciones y las propiedades de
uso interno del sistema se filtran, porque no representan un valor medido.

### Mapa

Las entidades sobre la ciudad.

- Cartografía **OpenStreetMap** por defecto, sin ninguna clave de API y con proveedor configurable.
- **Agrupación de marcadores**, que es lo que permite mostrar miles de puntos sin que el mapa se
  vuelva inmanejable.
- Consulta por **recuadro visible**: al desplazar o hacer zoom se piden solo las entidades del área
  mostrada, y la petición anterior se cancela.
- Filtros de búsqueda y de modelo de datos, coherentes con los del listado.
- Ficha emergente por entidad con acceso directo a su detalle.

### Paneles de análisis

Los paneles son la parte de *business intelligence*: cada uno agrupa varias gráficas sobre las
medidas elegidas.

- Listado de paneles disponibles y vista de detalle con su disposición en rejilla, adaptada al ancho
  de la pantalla.
- Tipos de gráfica: **línea, barras, sectores, indicador de aguja, cifra de resumen y tabla**.
- **Selector de rango** (24 h, 7, 30 y 90 días) con **agregación automática**: el intervalo crece con
  la ventana pedida, de modo que una consulta de 90 días no intenta dibujar cientos de miles de
  puntos.
- Tope de puntos por serie y consulta descendente, para conservar siempre lo más reciente.
- Un panel cuyo tipo de gráfica no se reconoce **se indica como tal y no rompe la pantalla**; el
  resto del panel sigue funcionando.

Los paneles además se **crean desde la propia aplicación** —en blanco o a partir de una plantilla—,
se renombran, y admiten añadir una gráfica sobre una medida y retirarla.

### Alarmas

- Listado de alarmas con su estado —activa o desactivada, disparada o en reposo— y búsqueda.
- Detalle con sus **condiciones legibles**: umbrales con su operador, condiciones de inactividad con
  su tiempo de espera, y las restricciones temporales que las acotan (meses, días de la semana,
  franjas horarias).
- **Histórico de estado** en el rango elegido. Si el despliegue no tiene configurados los
  identificadores que ese histórico necesita, la pantalla **explica por qué no puede mostrarlo** en
  lugar de dibujar una gráfica vacía.

Esta versión consulta alarmas; no las crea ni las modifica.

### Preferencias

- **Tema claro u oscuro**, con previsualización inmediata.
- **Huso horario** y **formato de fecha**: todas las marcas temporales de la aplicación se muestran
  en el huso de la persona, no en el del servidor.
- **Formato de número**.
- Las preferencias se guardan en la cuenta, así que acompañan a la persona entre navegadores y
  dispositivos.

### Transversal a toda la aplicación

- **Interfaz en español**, con las URL también en español.
- **Tema claro y oscuro** en todas las pantallas, con la paleta comprobada contra WCAG 2.1 AA.
- **Diseño adaptable** verificado a 390 px de ancho.
- **Cuatro estados en cada pantalla** —cargando, vacío, error y con datos—, con mensajes de error
  que distinguen un fallo de red de una falta de permisos y ofrecen reintentar.
- **Inicio de sesión OIDC** con renovación de token transparente.

---

## Arquitectura

**Vue 3** con TypeScript, compuesta con **Vuetify 3** y empaquetada con **Vite**. Es una **SPA
monolítica**: un único proyecto que se construye a un directorio de ficheros estáticos y consume
una **API REST** y un **proveedor de identidad OIDC**, ambos externos.

```
   navegador
   ┌──────────────────────────────────────────┐
   │  PID-GIJÓN (ficheros estáticos)          │
   │  vistas ── stores ── capa api ── axios ──┼──► API REST   /api/V1
   │                └──── cliente OIDC ───────┼──► Keycloak
   └──────────────────────────────────────────┘
                                              └──► teselas de mapa
```

No hay servidor propio, ni proceso de Node en ejecución, ni base de datos. Se publica en cualquier
servidor web.

El código se organiza por **funcionalidad**, no por tipo de fichero: cada una vive en
`src/features/<nombre>/` con sus rutas, sus textos, sus llamadas a la API, sus componentes y sus
vistas. Se registra con dos líneas en el enrutador y dos en el módulo de textos, y se puede borrar
quitando su carpeta.

| Pieza | Dónde | Papel |
| --- | --- | --- |
| Cliente HTTP | `src/api/http.ts` | Token, renovación, clasificación de errores |
| Autenticación | `src/auth/keycloak.ts` | OIDC con PKCE |
| Tema y componentes | `src/plugins/vuetify.ts` | Paleta y valores por defecto |
| Estado | `src/stores/` | Sesión e interfaz |
| Estados de pantalla | `src/components/StateBlock.vue` | Cargando, vacío, error, contenido |
| Tipos del dominio | `src/types/index.ts` | Contrato interno compartido |

Tres decisiones que conviene conocer antes de tocar el código:

1. **Un monolito modular, a propósito.** Quien reciba esto debe poder clonar, `npm install`,
   `npm run dev` y tenerlo todo funcionando. El razonamiento completo está en
   [docs/architecture.md](docs/architecture.md#2-por-qué-un-monolito).
2. **La capa api propaga la excepción; nunca devuelve `null` en un fallo.** Devolver `null` haría
   indistinguible «no hay datos» de «ha fallado», y eso acaba en pantallas que dicen «sin
   resultados» cuando el servidor está caído.
3. **Sin CSS a medida.** Todo el aspecto sale del tema y de los valores por defecto de Vuetify. Es
   lo que permite cambiar la paleta de la aplicación entera desde un fichero. Véase
   [docs/design-system.md](docs/design-system.md).

---

## Estándares abiertos

La aplicación no inventa su propio modelo de datos: consume datos ya normalizados según estándares
abiertos, y eso es lo que la hace reutilizable en otro municipio.

### NGSI-LD

El modelo de información es **NGSI-LD**, la especificación de gestión de contexto de **ETSI**
(*ETSI GS CIM 009*), que es el estándar de facto de las plataformas de ciudad inteligente europeas y
el que recomiendan las iniciativas de interoperabilidad de datos urbanos.

En la práctica, dentro de la aplicación:

- Cada elemento medido es una **entidad** con un identificador estable en forma de **URN**
  (`urn:ngsi-ld:AirQualityObserved:...`), un **tipo** y un conjunto de **atributos**.
- Se distingue entre **propiedades** (un valor observado, con su unidad y su marca temporal) y
  **relaciones** (un enlace a otra entidad). Solo las propiedades se muestran como medidas.
- La ubicación es una **GeoProperty** con geometría GeoJSON, que es lo que permite dibujar el mapa
  sin traducción alguna.

Documentación pública del estándar:
[ETSI ISG CIM](https://www.etsi.org/committee/cim) ·
[FIWARE NGSI-LD](https://fiware-datamodels.readthedocs.io/)

### Smart Data Models

El **tipo** de cada entidad procede de la iniciativa **Smart Data Models**, el catálogo abierto de
modelos de datos gobernado por FIWARE, TM Forum, IUDX e ITU-T. Son los esquemas que fijan qué
atributos tiene una estación de calidad del aire, un contenedor de residuos o un punto de medida de
ruido, y cómo se llaman.

Por qué importa aquí: **la aplicación es agnóstica del tipo de sensor**. No hay una pantalla para
calidad del aire y otra para ruido; hay una pantalla de entidad que muestra los atributos que el
modelo declare. Añadir una vertical nueva a la ciudad no exige tocar el cliente. Y un panel
construido en Gijón sobre `AirQualityObserved` significa lo mismo en cualquier otra ciudad que use
ese modelo.

- Catálogo: **<https://smartdatamodels.org>**
- Esquemas y contribuciones: <https://github.com/smart-data-models>
- Dominio de ciudad: <https://github.com/smart-data-models/dataModel.Environment>

Los Smart Data Models se publican bajo **CC BY 4.0**.

### Otros estándares presentes

| Estándar | Uso |
| --- | --- |
| **OpenID Connect** / OAuth 2.0 con PKCE | Autenticación |
| **GeoJSON** (RFC 7946) | Geometrías de las entidades |
| **ISO 8601** | Marcas temporales e intervalos de agregación (`PT1H`, `PT24H`) |
| **WCAG 2.1 AA** | Contraste y accesibilidad de la interfaz |
| **IANA Time Zones** | Husos horarios de las preferencias |

---

## Requisitos

| Herramienta | Versión | Para qué |
| --- | --- | --- |
| **Node.js** | **20 o superior** | Desarrollo y construcción |
| npm | 10 o superior | Viene con Node 20 |

Nada más: no hace falta Docker, ni base de datos, ni ningún servicio local. Sí hacen falta, en
tiempo de ejecución, una **API REST** y un **proveedor de identidad** accesibles, y sus URL en el
fichero `.env`.

En el navegador: cualquier versión reciente de Chrome, Firefox, Edge o Safari (últimas dos
versiones). No hay soporte para Internet Explorer.

---

## Arranque

La interfaz web es un componente del monorepo de la plataforma, así que se trabaja desde su propia
carpeta:

```bash
git clone <url-del-repositorio> pid-gijon
cd pid-gijon/frontend

npm install

cp .env.example .env    # rellena los valores de tu entorno

npm run dev             # http://localhost:20600
```

El puerto **20600** no es casual: el origen de desarrollo tiene que estar dado de alta en la
configuración CORS de la API **y** entre las URI de redirección válidas del cliente OIDC. Si lo
cambias, cámbialo también allí o el inicio de sesión fallará.

### Guiones disponibles

| Guion | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo con recarga en caliente, puerto 20600 |
| `npm run build` | Comprueba tipos y empaqueta en `dist/` |
| `npm run preview` | Sirve `dist/` para revisar el artefacto construido |
| `npm run typecheck` | `vue-tsc --noEmit`, plantillas incluidas |
| `npm run licenses` | Vuelca el árbol de dependencias y sus licencias |

---

## Variables de entorno

Toda la configuración entra por variables `VITE_*`, declaradas en
[`.env.example`](.env.example) y tipadas en [`env.d.ts`](env.d.ts). Copia la plantilla a `.env` y
rellénala; `.env` está fuera del control de versiones.

> **Importante.** Estas variables se **incrustan en el paquete al construir** y viajan al navegador:
> son públicas. Solo se ponen aquí URL, identificadores públicos de cliente OIDC y parámetros de
> mapa. **Ninguna credencial, ningún secreto.** Y cambiar cualquiera de ellas exige **reconstruir**.

### API

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Sí | Origen de la API REST, **sin** la ruta. El cliente añade `/api/V1`. Ejemplo: `https://api.example.org`. Este origen tiene que aceptar el origen de la aplicación por CORS y permitir la cabecera `Authorization`. |

### Identidad (OIDC / Keycloak)

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `VITE_OIDC_URL` | Sí | URL base del proveedor de identidad. Ejemplo: `https://auth.example.org`. |
| `VITE_OIDC_REALM` | Sí | Nombre del *realm* donde vive el cliente. |
| `VITE_OIDC_CLIENT_ID` | Sí | Identificador del cliente público registrado para esta aplicación. Es público por diseño: la seguridad del flujo la dan PKCE y la lista de URI de redirección registradas, no un secreto. |

El cliente tiene que estar dado de alta como **público**, con **flujo estándar** activado, **PKCE
`S256`** y el origen de la aplicación entre sus URI de redirección válidas —incluida la de cierre de
sesión, que apunta a `/login`—.

### Cartografía

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `VITE_MAP_TILES_URL` | Sí | Plantilla de URL de las teselas, con `{s}`, `{z}`, `{x}` e `{y}`. Por defecto OpenStreetMap, que **no requiere ninguna clave**: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`. |
| `VITE_MAP_TILES_ATTRIBUTION` | Sí | Texto de atribución que se muestra sobre el mapa. Con OpenStreetMap: `&copy; colaboradores de OpenStreetMap`. **Es obligatorio por los términos de uso y no debe retirarse**; si cambias de proveedor, cambia también este texto y actualiza [`NOTICE.md`](../NOTICE.md). |
| `VITE_MAP_DEFAULT_CENTER` | Sí | Centro inicial, `latitud,longitud`. Por defecto `43.5322,-5.6611` (Gijón). |
| `VITE_MAP_DEFAULT_ZOOM` | Sí | Nivel de zoom inicial. Por defecto `13`, que encuadra el término municipal. |

### Datos en vivo (opcional)

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `VITE_REALTIME_URL` | No | Servidor de datos en vivo. Si va vacío, la lectura es a demanda por HTTP, que es el modo por defecto. La credencial de esa conexión **no va aquí**: se pide a la API en tiempo de ejecución, una vez hay sesión. |

### Identificadores técnicos del backend

No son nombres de producto: son **claves de datos** que ya existen en el sistema con el que la
aplicación se integra. Se leen del entorno, y no del código, para que el repositorio publicado no
quede atado a los identificadores de un despliegue concreto. Se dejan **sin valor por defecto a
propósito**: si faltan, la funcionalidad que depende de ellos se degrada de forma explícita —lo dice
en pantalla—, nunca en silencio. Véase
[`src/api/platform-contract.ts`](src/api/platform-contract.ts).

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `VITE_DATA_SCOPE_PREFERENCE_KEY` | No | Clave de la preferencia de usuario que fija el ámbito de datos. La necesita el histórico de alarmas. |
| `VITE_ALARM_ENTITY_TYPE` | No | Tipo de entidad NGSI-LD bajo el que el backend publica el estado de una alarma. Sin ella no se puede construir el URN del histórico de estado. |

---

## Construcción y despliegue

```bash
npm ci
npm run build      # comprueba tipos y genera dist/
```

`dist/` son ficheros estáticos: se sirven desde cualquier servidor web o almacenamiento de objetos.
**El servidor tiene que reescribir las rutas de navegación a `index.html`**; si no, la aplicación
devuelve un 404 al recargar una página interna.

El procedimiento completo —configuración de nginx y de Apache, cabeceras y política de contenido
recomendadas, URI de redirección y CORS que hay que dar de alta, política de caché y la lista de
comprobación posterior al despliegue— está en **[docs/deployment.md](docs/deployment.md)**.

---

## Documentación

| Documento | Contenido |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Estructura de carpetas, por qué un monolito, agregación de rutas y textos, gestión de errores, autenticación OIDC |
| [`openapi-gestion.yaml`](../openapi-gestion.yaml) | Contrato de la API que consume la aplicación: rutas, parámetros y forma de las respuestas (en la raíz del repositorio) |
| [docs/design-system.md](docs/design-system.md) | Paleta con sus ratios de contraste, valores por defecto de Vuetify y las cinco reglas de composición |
| [docs/deployment.md](docs/deployment.md) | Construcción, servicio de ficheros estáticos, cabeceras, comprobación posterior |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo contribuir y qué comprobaciones son obligatorias |
| [`SECURITY.md`](../SECURITY.md) | Cómo informar de una vulnerabilidad (raíz del repositorio) |
| [ASSETS.md](ASSETS.md) | Registro de recursos gráficos con su origen y su licencia |
| [`NOTICE.md`](../NOTICE.md) | Titularidad y atribuciones obligatorias de terceros |
| [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md) | Dependencias y sus licencias |

---

## Procedencia del código

Este apartado se declara por escrito porque el repositorio es público y el destinatario es una
administración.

**El código de esta aplicación es original.** Se ha escrito para este proyecto: los componentes,
las vistas, la capa de acceso a la API, el tema visual, los textos de interfaz y la documentación.

**La única entrada externa ha sido la especificación HTTP de la API REST** con la que la aplicación
se integra: qué endpoints existen, qué parámetros aceptan y qué forma tienen sus respuestas. Sobre
esa especificación se ha implementado un cliente desde cero, documentado en
[`openapi-gestion.yaml`](../openapi-gestion.yaml).

**No se ha reutilizado código, hojas de estilo, plantillas de interfaz, iconos ni recursos gráficos
de ningún producto comercial o propietario.** En concreto:

- El aspecto no procede de ninguna plantilla de interfaz de pago. Sale del tema y de los valores por
  defecto de Vuetify definidos en [`src/plugins/vuetify.ts`](src/plugins/vuetify.ts), y no hay
  ninguna hoja de estilo propia.
- La paleta se ha definido para este proyecto y sus ratios de contraste están calculados y
  documentados en [docs/design-system.md](docs/design-system.md).
- El único recurso gráfico del repositorio es el favicon, original del proyecto y registrado en
  [ASSETS.md](ASSETS.md).
- No se carga ninguna tipografía comercial ni ningún recurso desde una CDN de terceros.

**Las dependencias de terceros son todas software libre con licencia permisiva**, se incorporan como
paquetes públicos de npm sin modificar, y están enumeradas con su versión y su licencia en
[THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md): 123 paquetes en el árbol instalado —105 de ellos
en el árbol de producción, el que alimenta el artefacto publicado—, todos MIT, Apache-2.0, BSD, ISC
o 0BSD. **Ninguna dependencia con licencia copyleft ni de uso restringido**, de modo que nada impide
distribuir el conjunto bajo EUPL-1.2.

Las atribuciones obligatorias —la cartografía de OpenStreetMap y las bibliotecas principales— están
en [`NOTICE.md`](../NOTICE.md).

---

## Licencia

Distribuido bajo la **Licencia Pública de la Unión Europea v. 1.2 (EUPL-1.2)**.

    Licensed under the EUPL

El texto íntegro está en el [`LICENSE`](../LICENSE) de la raíz del repositorio. Identificador SPDX: `EUPL-1.2`.

La EUPL es la licencia de software libre de la Comisión Europea, la habitual en la contratación
pública europea. Está publicada en las **23 lenguas oficiales de la Unión y todas las versiones
tienen el mismo valor jurídico**; el fichero `LICENSE` recoge la versión inglesa. La versión
española y el resto están disponibles en la página oficial:
<https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>

En resumen —y sin que este resumen sustituya al texto de la licencia—: puedes usar, copiar,
modificar y redistribuir esta aplicación, incluso con fines comerciales, siempre que **mantengas la
licencia** al distribuir la obra o sus derivados, **conserves los avisos de autoría** y ofrezcas el
código fuente. La EUPL es compatible con otras licencias copyleft recogidas en su apéndice, lo que
facilita reutilizar este código en otros proyectos públicos.

El software se distribuye **«tal cual», sin garantías de ningún tipo** (artículos 7 y 8 de la
Licencia).

---

## Titularidad

Copyright © 2026 **Ayuntamiento de Gijón / Xixón**.

Este software se ha desarrollado para el Ayuntamiento de Gijón en el marco del proyecto PID-GIJÓN, y
la titularidad de todo lo realizado para el proyecto le corresponde. Los detalles, junto con las
atribuciones de terceros, están en [`NOTICE.md`](../NOTICE.md).

Se publica como software libre para que cualquier administración pueda reutilizarlo, adaptarlo a su
propia red de sensores y contribuir sus mejoras.
