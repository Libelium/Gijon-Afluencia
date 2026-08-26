# Sistema de diseño

Todo lo que define el aspecto de la aplicación vive en un único fichero:
[`src/plugins/vuetify.ts`](../src/plugins/vuetify.ts). Ahí están la paleta de los dos temas y
los `defaults` de los componentes. Esta página documenta esos valores y las reglas de
composición que los acompañan.

La consecuencia práctica: **no hay hojas de estilo propias**. La aplicación no tiene un
`main.scss`, ni variables CSS propias, ni bloques `<style>` salvo en los casos justificados que
recoge la Regla 1: dar altura al contenedor del mapa y al de una gráfica —que no la deducen de su
contenido— y reconducir al tema el DOM que genera una biblioteca de terceros. Si algo hay que
cambiar de aspecto, se cambia en el tema o en los `defaults`, no en la vista.

---

## 1. Paleta

Dos temas, `light` (por defecto) y `dark`. El usuario los alterna desde la barra superior y la
elección se guarda en `localStorage` a través de `useUiStore()`; la preferencia
`displayskinMode` de la cuenta gana la primera vez que se monta la aplicación.

### Tema claro

| Token | Valor | Papel |
| --- | --- | --- |
| `background` | `#F6F7F9` | Fondo de la página |
| `surface` | `#FFFFFF` | Tarjetas, diálogos, menús |
| `surface-variant` | `#ECEEF1` | Superficie secundaria (avatares, celdas destacadas) |
| `on-surface-variant` | `#42474E` | Texto sobre `surface-variant` |
| `primary` | `#B3261E` | Acción principal |
| `on-primary` | `#FFFFFF` | Texto sobre `primary` |
| `secondary` | `#3E5C76` | Acción secundaria, series de datos |
| `on-secondary` | `#FFFFFF` | Texto sobre `secondary` |
| `error` | `#B3261E` | Error |
| `success` | `#1B6B45` | Estado correcto |
| `warning` | `#E8A32B` | Aviso |
| `info` | `#1C5E85` | Información |
| `on-background` / `on-surface` | `#1A1C1E` | Texto principal |
| `outline` | `#DDE0E4` | Bordes de tarjeta, separadores |
| `outline-strong` | `#767C85` | Bordes de control, iconos de baja emisión |
| `muted` | `#5A6068` | Texto secundario |

### Tema oscuro

| Token | Valor | Papel |
| --- | --- | --- |
| `background` | `#121316` | Fondo de la página |
| `surface` | `#1B1D21` | Tarjetas, diálogos, menús |
| `surface-variant` | `#24272C` | Superficie secundaria |
| `on-surface-variant` | `#C7CBD1` | Texto sobre `surface-variant` |
| `primary` | `#FF8A7A` | Acción principal |
| `on-primary` | `#3A0B08` | Texto sobre `primary` |
| `secondary` | `#8FB3CE` | Acción secundaria, series de datos |
| `on-secondary` | `#12212B` | Texto sobre `secondary` |
| `error` | `#FF8A7A` | Error |
| `success` | `#6BCF9B` | Estado correcto |
| `warning` | `#F2C25B` | Aviso |
| `info` | `#7EC0E8` | Información |
| `on-background` / `on-surface` | `#E6E8EB` | Texto principal |
| `outline` | `#2E3238` | Bordes de tarjeta, separadores |
| `outline-strong` | `#7A818A` | Bordes de control |
| `muted` | `#A3A9B1` | Texto secundario |

En oscuro los colores de estado se aclaran: el mismo `#B3261E` sobre `#1B1D21` daría 2,1:1 y
sería ilegible. Por eso `primary` pasa a `#FF8A7A` y las parejas `on-*` se oscurecen.

### Contraste

Requisito de referencia: **WCAG 2.1 AA** — 4,5:1 para texto normal, 3:1 para texto grande y para
los límites de los controles. Ratios calculados sobre los valores de arriba:

| Tema | Pareja | Ratio | AA |
| --- | --- | --- | --- |
| claro | `on-surface` sobre `surface` | 17,09:1 | sí |
| claro | `on-surface` sobre `background` | 15,94:1 | sí |
| claro | `muted` sobre `surface` | 6,35:1 | sí |
| claro | `muted` sobre `background` | 5,92:1 | sí |
| claro | `primary` sobre `surface` | 6,54:1 | sí |
| claro | `on-primary` sobre `primary` | 6,54:1 | sí |
| claro | `secondary` sobre `surface` | 7,01:1 | sí |
| claro | `success` sobre `surface` | 6,49:1 | sí |
| claro | `info` sobre `surface` | 7,03:1 | sí |
| claro | `on-warning` sobre `warning` | 7,90:1 | sí |
| claro | `on-surface-variant` sobre `surface-variant` | 8,05:1 | sí |
| claro | `outline-strong` sobre `surface` | 4,21:1 | sí (3:1, no textual) |
| oscuro | `on-surface` sobre `surface` | 13,75:1 | sí |
| oscuro | `on-surface` sobre `background` | 15,13:1 | sí |
| oscuro | `muted` sobre `surface` | 7,13:1 | sí |
| oscuro | `muted` sobre `background` | 7,84:1 | sí |
| oscuro | `primary` sobre `surface` | 7,37:1 | sí |
| oscuro | `on-primary` sobre `primary` | 7,45:1 | sí |
| oscuro | `secondary` sobre `surface` | 7,64:1 | sí |
| oscuro | `success` sobre `surface` | 8,86:1 | sí |
| oscuro | `info` sobre `surface` | 8,51:1 | sí |
| oscuro | `warning` sobre `surface` | 10,16:1 | sí |
| oscuro | `on-surface-variant` sobre `surface-variant` | 9,20:1 | sí |
| oscuro | `outline-strong` sobre `surface` | 4,29:1 | sí (3:1, no textual) |

Dos avisos que se deducen de la tabla:

- **`outline` no es un color de texto ni de control.** `#DDE0E4` sobre blanco es 1,32:1 y
  `#2E3238` sobre `#1B1D21` es 1,31:1: sirve solo para el borde decorativo de una tarjeta o un
  separador. Cuando el borde tiene que *comunicar* (el límite de un campo de formulario, el
  contorno de un elemento con foco), el token es `outline-strong`.
- **`warning` en tema claro no vale como texto sobre superficie**: `#E8A32B` sobre blanco es
  2,16:1. Se usa como relleno con `on-warning` encima (7,90:1) o como color de icono acompañado
  de texto en `on-surface`. Nunca como color de una frase.

Si se cambia un color, hay que recalcular la pareja completa. El cálculo es el estándar de
luminancia relativa de WCAG; los valores de esta tabla se han obtenido con él y no a ojo.

---

## 2. Valores por defecto de los componentes

Están en el bloque `defaults` de `createVuetify()`. Su razón de ser es que **las vistas no
repitan props de estilo**: una vista escribe `<VCard>` y ya sale plana, con borde y esquinas
`lg`; escribe `<VTextField>` y ya sale `outlined` con densidad `comfortable`.

| Componente | Defaults | Efecto |
| --- | --- | --- |
| `VCard` | `variant: 'flat'`, `border: true`, `rounded: 'lg'` | Tarjeta con borde de 1 px y **sin sombra** |
| `VBtn` | `variant: 'flat'`, `rounded: 'md'`, `class: 'text-none'` | Botón plano, sin mayúsculas forzadas |
| `VTextField`, `VSelect`, `VAutocomplete`, `VTextarea` | `variant: 'outlined'`, `density: 'comfortable'`, `hideDetails: 'auto'` | Campos con contorno; el hueco del mensaje de ayuda solo aparece si hay mensaje |
| `VDataTable`, `VDataTableServer` | `density: 'comfortable'`, `hover: true` | Tablas legibles, fila resaltada al pasar el ratón |
| `VChip` | `size: 'small'`, `rounded: 'sm'` | Etiqueta compacta |
| `VToolbar` | `color: 'transparent'`, `density: 'comfortable'` | Barra sin fondo propio |
| `VAppBar` | `flat: true`, `border: 'b'` | Cabecera separada por línea, no por sombra |
| `VNavigationDrawer` | `border: 'e'` | Menú lateral separado por línea |
| `VList`, `VTabs` | `density: 'comfortable'` | Densidad homogénea con el resto |
| `VAlert` | `variant: 'tonal'`, `rounded: 'lg'` | Aviso de fondo suave, no saturado |
| `VDialog` | `maxWidth: 720` | Diálogo que no se estira en pantallas anchas |

Iconografía: conjunto `mdi` (Material Design Icons) cargado como tipografía, con los alias de
Vuetify. Los nombres se escriben completos (`mdi-map-outline`).

Tipografía: la de Vuetify por defecto (Roboto y la pila de sistema). **No se carga ninguna
fuente comercial ni ningún recurso tipográfico de un tercero desde una CDN**; el arranque de la
aplicación no depende de ninguna descarga externa más allá de las teselas del mapa.

---

## 3. Las cinco reglas de composición

### Regla 1 — Sin CSS a medida

Se compone con props de Vuetify y con las utilidades nativas de espaciado y disposición
(`pa-4`, `px-6`, `mb-5`, `ga-3`, `d-flex`, `flex-wrap`, `align-center`, `text-truncate`). Escribir
un bloque `<style>` es la excepción, y solo está justificada en dos supuestos:

1. **Altura que el contenedor no puede deducir de su contenido**: el mapa y el lienzo de una
   gráfica. Sin una altura explícita, Leaflet no se dibuja.
2. **DOM generado por una biblioteca de terceros**, al que no llega ninguna prop de Vuetify.
   Leaflet crea sus marcadores, sus globos de agrupación y sus bocadillos como HTML propio: su
   aspecto se reconduce a los tokens del tema con `:deep`, no se deja con el de la biblioteca.
   Es el único sitio donde ocurre (`src/features/map/views/MapView.vue`).

Todo lo demás —colores, radios, bordes, densidades— sale del tema y de los `defaults`. Y también
en la excepción se usan los tokens (`rgb(var(--v-theme-*))`), nunca un color literal.

Motivo: es lo que hace que un cambio de paleta o de densidad se aplique a toda la aplicación
desde un fichero, y lo que evita que el tema oscuro se rompa en una pantalla concreta.

### Regla 2 — El rojo se reserva

`primary` es rojo y `error` es el mismo rojo. Eso obliga a ser estricto: el rojo marca **la
acción principal de la pantalla** (una por pantalla) y **el error**. Nada más. Las acciones
secundarias van en `variant="tonal"` o `variant="text"`, y los elementos de navegación activos
usan `color="primary"` como acento de un solo elemento, no como fondo de una zona.

Una interfaz de datos pintada de rojo se lee como una interfaz en alarma permanente. Los estados
tienen sus propios tokens (`success`, `warning`, `info`) precisamente para no recurrir al rojo.

### Regla 3 — Jerarquía por escala, nunca por tamaños sueltos

El texto usa las clases de la escala tipográfica: `text-h6` para el título de una pantalla o de
una tarjeta, `text-subtitle-2` para un encabezado menor, `text-body-1` y `text-body-2` para el
cuerpo, `text-caption` para lo accesorio. La emisión se baja con `text-medium-emphasis` (o con el
token `muted`), no con un gris inventado. El peso, con `font-weight-medium`.

Está prohibido escribir `font-size` o `color` a mano. Si una jerarquía no se puede expresar con
la escala, el problema es la jerarquía.

### Regla 4 — Cuatro estados en toda pantalla, con `StateBlock`

Cargando, vacío, error y con datos. Los cuatro se resuelven con
[`src/components/StateBlock.vue`](../src/components/StateBlock.vue), que recibe `loading`,
`error`, `empty`, `emptyText`, `emptyIcon` y `skeleton` (`'table' | 'card' | 'text'`), emite
`retry` y expone el contenido en su slot por defecto y una acción opcional en el slot
`empty-action`.

```vue
<StateBlock :loading="loading" :error="error" :empty="!rows.length" skeleton="table" @retry="load">
  <VDataTable :items="rows" :headers="headers" />
</StateBlock>
```

Nadie inventa su propio esqueleto, su propio `VAlert` de error ni su propio mensaje de vacío. El
esqueleto de carga tiene la forma del contenido que va a sustituir, el error siempre ofrece
reintentar y el vacío explica qué falta, no solo que no hay nada.

### Regla 5 — Espaciado deliberado, y a 390 px también

El espacio entre hermanos se pone con el `gap` del contenedor (`ga-2`, `ga-3`, `ga-4`), no con
márgenes por hijo; el espacio interior, con el `padding` del propio elemento. Nunca las dos cosas
a la vez sobre el mismo eje. Los valores salen de la escala de Vuetify (`0`–`16`, múltiplos de
4 px), no de píxeles sueltos.

Nada se entrega pegado: ni dos botones entre sí, ni un icono con su texto, ni el contenido de una
tarjeta con su borde. La referencia son las cabeceras del propio proyecto:
[`PageHeader.vue`](../src/components/PageHeader.vue) usa `d-flex flex-wrap align-center ga-3 mb-5`
y el contenedor principal `pa-4 pa-md-6`.

Y se comprueba a **390 px de ancho**: `flex-wrap` en toda fila de controles, `text-truncate` con
`min-w-0` en todo texto que pueda ser largo, tablas con su propio contenedor de desplazamiento
horizontal. El `body` no puede desplazarse en horizontal en ningún caso. Es en móvil donde el
espaciado se rompe primero, cuando una fila de botones envuelve y pierde su separación.

---

## 4. Comprobaciones antes de dar una pantalla por terminada

- Los cuatro estados se han visto, no solo el estado con datos.
- Tema claro y tema oscuro: ningún texto pierde contraste, ningún borde desaparece.
- 390 px: sin desplazamiento horizontal del `body`, sin texto recortado ni solapado, controles
  alcanzables y con separación visible.
- Ningún bloque `<style>` nuevo salvo los supuestos de la Regla 1 (altura de mapa o de gráfica,
  o DOM de una biblioteca de terceros reconducido a los tokens del tema).
- Ningún color literal fuera de `src/plugins/vuetify.ts`.
