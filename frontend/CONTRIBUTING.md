# Cómo contribuir a la interfaz web

> Estas son las normas propias de este componente. Las transversales del repositorio —licencia de
> las aportaciones, ficheros de bloqueo, documentación que hay que mantener viva y convenciones de
> git— están en el [`CONTRIBUTING.md`](../CONTRIBUTING.md) de la raíz.

Gracias por el interés. Este proyecto se desarrolla para el Ayuntamiento de Gijón y se publica
como software libre bajo **EUPL-1.2**: las aportaciones son bienvenidas y se rigen por esa
licencia.

## Antes de escribir código

- Para un cambio pequeño y evidente (una errata, un texto, un fallo con reproducción clara), abre
  directamente la propuesta de cambio.
- Para un cambio de alcance —una funcionalidad nueva, un cambio de dependencia, una modificación
  de la paleta o del contrato con la API—, **abre antes una incidencia y acuerda el enfoque**. Es
  frustrante para todos revisar un trabajo grande que va en una dirección que no encaja.
- Si has encontrado un problema de seguridad, **no abras una incidencia**: sigue
  [`SECURITY.md`](../SECURITY.md).

## Poner en marcha el entorno

```bash
npm install
cp .env.example .env    # y rellena los valores de tu despliegue
npm run dev             # http://localhost:20600
```

Necesitas **Node 20 o superior**. Las variables están explicadas una a una en el
[README](README.md#variables-de-entorno).

## Comprobaciones obligatorias

Ejecuta las tres antes de proponer el cambio. Ninguna admite excepciones.

```bash
npm run typecheck     # vue-tsc en modo estricto, plantillas incluidas
npm run build         # comprueba tipos y empaqueta
```

No hay linter configurado: el estilo se sostiene imitando el código de alrededor y la
comprobación estricta de tipos. Si se añade uno, debe pasar limpio sobre todo el código antes de
darlo por bueno.

Y una que no automatiza ninguna herramienta: **prueba la pantalla en el navegador**, con datos y
sin ellos, en **tema claro y oscuro**, y a **390 px de ancho**. Un cambio que compila pero deja el
texto recortado en móvil no está terminado.

## Convenciones de código

Las reglas completas están en [docs/architecture.md](docs/architecture.md) y en
[docs/design-system.md](docs/design-system.md). El resumen:

- **TypeScript estricto.** Nada de `any`. Los tipos del dominio compartidos viven en
  `src/types/index.ts`; los que solo entiende una funcionalidad, en su carpeta.
- **La capa api propaga la excepción**, nunca devuelve `null` en un fallo: eso haría
  indistinguible «no hay datos» de «ha fallado».
- **Estados de pantalla con `StateBlock`**, siempre los cuatro: cargando, vacío, error y con
  datos. No inventes tu propio esqueleto ni tu propio aviso de error.
- **Sin CSS a medida.** Se compone con props de Vuetify y utilidades de espaciado (`pa-4`, `ga-3`,
  `mb-6`, `d-flex`). Un bloque `<style>` solo se justifica para dar altura al contenedor de un mapa
  o de una gráfica, o para reconducir al tema el DOM que genera una biblioteca de terceros —Leaflet
  es el único caso—. Ningún color literal fuera de `src/plugins/vuetify.ts`.
- **El rojo se reserva** para la acción principal y para el error. No pintes la interfaz de rojo.
- **Jerarquía con la escala tipográfica** (`text-h6`, `text-body-2`, `text-medium-emphasis`), nunca
  con tamaños sueltos.
- **Espaciado deliberado**: el `gap` del contenedor separa hermanos, el `padding` separa el
  contenido de su propio borde; nunca los dos sobre el mismo eje. Nada se entrega pegado.
- **Textos de interfaz en español**, en el fragmento `i18n.ts` de la funcionalidad, con las claves
  prefijadas. Nada de cadenas escritas directamente en la plantilla.
- **Comentarios solo cuando aportan.** Explica el *porqué* de una decisión que no se deduce
  leyendo el código; no describas lo que la línea ya dice. Una o dos líneas, en español.
- **Sin dependencias nuevas** salvo acuerdo previo. Cada paquete añadido es superficie de
  seguridad, peso de descarga y una fila más en THIRD-PARTY-LICENSES.md. Casi todo se resuelve con lo
  que ya hay.

## Estructura de una funcionalidad

Una funcionalidad es autocontenida:

```
src/features/<nombre>/
├── routes.ts        rutas, con la URL en español
├── i18n.ts          textos, con las claves prefijadas
├── api/             llamadas HTTP propias
├── components/      componentes que solo usa esta funcionalidad
└── views/           pantallas
```

Se registra con dos líneas: una importación y una expansión en `src/router/index.ts`, y lo mismo
en `src/i18n/index.ts`. Nada del núcleo importa desde `features/`, y una funcionalidad no importa
de otra: si algo hace falta en tres sitios, sube al núcleo.

## Aportaciones

- Una rama por cambio, con nombre descriptivo.
- **Mensajes de commit en imperativo y en español**, con una primera línea corta que diga qué
  cambia y por qué, no qué ficheros se han tocado.
- Cambios pequeños y revisables. Si la propuesta toca veinte ficheros por tres motivos distintos,
  sepárala en tres.
- No mezcles reformateo con cambio de comportamiento: la diferencia se vuelve ilegible.
- Actualiza la documentación en la misma aportación. Si añades una variable de entorno, va a
  `.env.example`, a `env.d.ts` y al README. Si añades un recurso gráfico, va a
  [ASSETS.md](ASSETS.md). Si añades una dependencia, va a
  [`THIRD-PARTY-LICENSES.md`](THIRD-PARTY-LICENSES.md) y al [`NOTICE.md`](../NOTICE.md) de la raíz.
- Describe en la propuesta **qué has probado**: navegadores, temas y anchos.

## Licencia de tu aportación

Al proponer un cambio aceptas que se distribuya bajo la **EUPL-1.2**, la licencia de este
repositorio, y confirmas que tienes derecho a aportarlo: que es obra tuya o que su origen es
compatible y está debidamente atribuido.

**No incorpores código, estilos ni recursos de productos comerciales o propietarios**, ni fragmentos
copiados de proyectos cuya licencia no permita esta redistribución. Si te has inspirado en una
fuente externa, dilo en la propuesta.
