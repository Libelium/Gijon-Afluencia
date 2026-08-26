# PID Gijón — dependencias de terceros y sus licencias

Este fichero declara el software de terceros del que depende la aplicación. Ninguna de estas
bibliotecas se ha modificado: se incorporan como paquetes públicos del registro npm y sus avisos de
copyright viajan dentro de cada paquete (`node_modules/<paquete>`).

Ninguna dependencia se redistribuye en este repositorio. El código de terceros se descarga en la
instalación (`npm ci`) y se empaqueta en el resultado del build.

- **Fecha de revisión:** 2026-08
- **Origen de los datos:** campo `license` del `package.json` de cada paquete del árbol instalado.

---

## 1. Resumen de compatibilidad

El árbol instalado suma **123 paquetes**, todos con licencia permisiva. De ellos, **105 están en el
árbol de producción** (`npm ls --omit=dev`), que es el que alimenta el artefacto publicado; los 18
restantes solo intervienen en la construcción y la comprobación de tipos:

| Licencia | Paquetes (árbol completo) | De los cuales, en producción |
| --- | --- | --- |
| MIT | 109 | 92 |
| Apache-2.0 | 6 | 6 |
| BSD-2-Clause | 2 | 2 |
| BSD-3-Clause | 2 | 2 |
| ISC | 2 | 1 |
| 0BSD | 1 | 1 |
| Apache-2.0 AND BSD-3-Clause | 1 | 1 |

No hay dependencias con licencia copyleft (GPL, LGPL, AGPL, MPL, EPL) ni propietaria o de uso
restringido, ni ningún paquete sin licencia declarada. Todas son compatibles con la distribución de
esta obra bajo **EUPL-1.2**: la EUPL permite incorporar componentes permisivos y solo obliga a
conservar sus avisos de copyright y de licencia, que es lo que hace este fichero junto con
[`NOTICE.md`](../NOTICE.md).

---

## 2. Dependencias de producción (directas)

Son las que viajan en el artefacto que se publica.

| Paquete | Versión | Licencia | Uso en la aplicación |
| --- | --- | --- | --- |
| `vue` | 3.5.41 | MIT | Framework de interfaz |
| `vue-router` | 4.6.4 | MIT | Enrutado de la SPA |
| `pinia` | 2.3.1 | MIT | Estado compartido (sesión, interfaz) |
| `vuetify` | 3.13.2 | MIT | Sistema de componentes y tema |
| `axios` | 1.20.0 | MIT | Cliente HTTP contra la API |
| `luxon` | 3.7.2 | MIT | Fechas, husos horarios y formato |
| `echarts` | 5.6.0 | Apache-2.0 | Gráficas de los paneles |
| `vue-echarts` | 7.0.3 | MIT | Envoltorio Vue de ECharts |
| `leaflet` | 1.9.4 | BSD-2-Clause | Mapa |
| `@vue-leaflet/vue-leaflet` | 0.10.1 | MIT | Envoltorio Vue de Leaflet |
| `leaflet.markercluster` | 1.5.3 | MIT | Agrupación de marcadores del mapa |
| `keycloak-js` | 26.2.4 | Apache-2.0 | Cliente OIDC (autenticación) |
| `@mdi/font` | 7.4.47 | Apache-2.0 | Iconografía Material Design Icons |

---

## 3. Dependencias de desarrollo (directas)

No forman parte del artefacto publicado; solo intervienen en la construcción y en la comprobación
de tipos.

| Paquete | Versión | Licencia | Uso |
| --- | --- | --- | --- |
| `vite` | 6.4.3 | MIT | Servidor de desarrollo y empaquetado |
| `@vitejs/plugin-vue` | 5.2.4 | MIT | Compilación de componentes Vue |
| `vite-plugin-vuetify` | 2.1.3 | MIT | Importación automática de Vuetify |
| `typescript` | 5.9.3 | Apache-2.0 | Lenguaje y comprobador de tipos |
| `vue-tsc` | 2.2.12 | MIT | Comprobación de tipos en `.vue` |
| `sass-embedded` | 1.103.1 | MIT | Compilación de los estilos de Vuetify |
| `@types/leaflet` | 1.9.22 | MIT | Tipos de Leaflet |
| `@types/leaflet.markercluster` | 1.5.6 | MIT | Tipos de markercluster |
| `@types/luxon` | 3.7.5 | MIT | Tipos de Luxon |

---

## 4. Dependencias transitivas no MIT

Se enumeran aparte porque su aviso de licencia no es el más frecuente del árbol.

| Paquete | Versión | Licencia | Nota |
| --- | --- | --- | --- |
| `@bufbuild/protobuf` | 2.14.0 | Apache-2.0 AND BSD-3-Clause | Vía `sass-embedded` |
| `detect-libc` | 2.1.2 | Apache-2.0 | |
| `entities` | 7.0.1 | BSD-2-Clause | |
| `minimatch` | 9.0.9 | ISC | |
| `picocolors` | 1.1.1 | ISC | |
| `rxjs` | 7.8.2 | Apache-2.0 | Vía `sass-embedded` |
| `source-map-js` | 1.2.1 | BSD-3-Clause | |
| `tslib` | 2.3.0 | 0BSD | |
| `zrender` | 5.6.1 | BSD-3-Clause | Motor de dibujo de ECharts |

---

## 5. Recursos que no son código

| Recurso | Licencia | Nota |
| --- | --- | --- |
| Cartografía OpenStreetMap | Datos ODbL 1.0 · teselas CC BY-SA 2.0 | Atribución obligatoria. Véase [NOTICE.md](../NOTICE.md), sección 4 |
| Smart Data Models | CC BY 4.0 | <https://smartdatamodels.org> |
| Recursos gráficos propios | — | Registrados en [ASSETS.md](ASSETS.md) |

---

## 6. Cómo regenerar el listado completo

Este fichero es la declaración revisada a mano. El volcado exhaustivo del árbol —incluidas todas
las transitivas, con su texto de licencia— se genera con:

```bash
npm run licenses
```

El resultado (`THIRD-PARTY-LICENSES.json`) **no se versiona**: es un artefacto derivado del árbol
instalado en cada máquina. Regenéralo y revisa este fichero cada vez que se añada, se elimine o se
actualice una dependencia directa.
