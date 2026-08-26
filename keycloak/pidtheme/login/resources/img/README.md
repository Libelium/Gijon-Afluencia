# Imágenes del tema

Los ficheros de esta carpeta son **marcadores de posición transparentes**, no arte final:

| Fichero | Uso |
| --- | --- |
| `logo.png` | Imagen de la capa de parallax del login y valor de `kcLogoLink` en `theme.properties` (login y email). |
| `favicon.ico` | Reservado para el icono de pestaña; hoy ninguna plantilla lo referencia. |

Sustitúyelos por el arte propio antes de desplegar, conservando los nombres de fichero
(o actualizando las referencias en `../../theme.properties` y `../../../login/template.ftl`).

Alternativa sin reconstruir la imagen: la variable de entorno `KC_BRAND_LOGIN_IMAGE` admite una
URL absoluta, una ruta absoluta o el nombre de un fichero de esta carpeta, y tiene prioridad sobre
`logo.png`. Los colores corporativos se ajustan con `KC_BRAND_PRIMARY`, `KC_BRAND_SECONDARY` y
`KC_BRAND_INDIGO`.
