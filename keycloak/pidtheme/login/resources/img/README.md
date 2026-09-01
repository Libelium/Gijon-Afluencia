# Imágenes del tema

| Fichero | Uso | Estado |
| --- | --- | --- |
| `logo.png` | Imagen de la capa de parallax del login y valor de `kcLogoLink` en `theme.properties` (login y email). | Logotipo de Gijón en blanco, 480 px de ancho. |
| `favicon.ico` | Reservado para el icono de pestaña; hoy ninguna plantilla lo referencia. | **Marcador de posición transparente.** |

`logo.png` está **en blanco a propósito**: se pinta sobre el degradado que el tema compone con
`KC_BRAND_INDIGO`, `KC_BRAND_SECONDARY` y `KC_BRAND_PRIMARY`, y la versión a color del logotipo
se perdería sobre él. Si cambias los colores de marca por otros claros, cambia también este
fichero por la variante que contraste.

Este logotipo es el **respaldo**: si la organización tiene la preferencia `themeLoginIcon`,
`js/dynamicLogo.js` la descarga del backend y sustituye la imagen en caliente, de modo que cada
organización ve la suya sin reconstruir la imagen del contenedor.

Al sustituir cualquiera de los dos ficheros, conserva el nombre (o actualiza las referencias en
`../../theme.properties` y `../../../login/template.ftl`).

Alternativa sin reconstruir la imagen: la variable de entorno `KC_BRAND_LOGIN_IMAGE` admite una
URL absoluta, una ruta absoluta o el nombre de un fichero de esta carpeta, y tiene prioridad sobre
`logo.png`. Los colores corporativos se ajustan con `KC_BRAND_PRIMARY`, `KC_BRAND_SECONDARY` y
`KC_BRAND_INDIGO`.
