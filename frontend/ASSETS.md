# Registro de recursos gráficos

Inventario de todo recurso gráfico que se distribuye con la aplicación, con su origen y su
licencia. **Un recurso que no esté en esta tabla no debe entrar en el repositorio.**

Este registro existe porque la aplicación se publica como software libre y se entrega a una
administración pública: cada imagen, icono o tipografía tiene que poder justificarse. Una imagen
sin procedencia acreditada es un riesgo legal, no un detalle.

## Recursos propios del proyecto

| Fichero | Tipo | Origen | Licencia |
| --- | --- | --- | --- |
| `public/favicon.svg` | SVG, 64×64 | Original, creado para este proyecto. Monograma «PID» sobre el rojo `#B3261E` de la paleta. | La de este repositorio (EUPL-1.2), titularidad del Ayuntamiento de Gijón |

Es hoy el único recurso gráfico propio. Todo lo demás que se ve en pantalla —iconos, gráficas,
mapa— se dibuja en tiempo de ejecución a partir de dependencias declaradas.

## Recursos de terceros que se dibujan en tiempo de ejecución

No son ficheros de este repositorio, pero forman parte de lo que ve el usuario y arrastran
obligaciones de atribución.

| Recurso | Procedencia | Licencia | Atribución |
| --- | --- | --- | --- |
| Iconografía Material Design Icons | Paquete npm `@mdi/font` | Apache-2.0 | En NOTICE y THIRD-PARTY-LICENSES |
| Teselas del mapa | OpenStreetMap (configurable) | Datos ODbL 1.0 · teselas CC BY-SA 2.0 | **Visible y permanente** en el control de atribución del mapa |
| Tipografía de interfaz | La de Vuetify: Roboto y la pila de fuentes del sistema | Apache-2.0 (Roboto) | No requiere aviso en pantalla |

Sobre el mapa: la atribución se toma de `VITE_MAP_TILES_ATTRIBUTION` y **no debe retirarse**. Si un
despliegue cambia el proveedor de teselas con `VITE_MAP_TILES_URL`, tiene que cambiar también ese
texto por el que exija el nuevo proveedor y actualizar la sección 4 de [NOTICE.md](../NOTICE.md).

## Reglas para añadir un recurso

1. **Prefiere no añadirlo.** Un icono de `@mdi/font` o una forma dibujada con Vuetify no añade
   ficheros ni obligaciones.
2. Si hace falta un fichero, tiene que ser **original del proyecto** o venir de una fuente con
   licencia compatible con EUPL-1.2 y que permita redistribución.
3. **Prohibido**: recursos de bancos de imágenes, plantillas de interfaz comerciales, iconos o
   tipografías de pago o con licencia de uso restringido, y logotipos de terceros sin permiso
   escrito.
4. Formato: **SVG** siempre que se pueda. Es nítido en cualquier densidad, pesa poco y se puede
   revisar en una diferencia de código.
5. Añade la fila a la tabla en la misma aportación que el fichero, con origen y licencia
   concretos. «Descargado de internet» no es un origen.
6. Si el recurso es de un tercero, añádelo también a la sección correspondiente de NOTICE.

## Logotipos institucionales

Este repositorio **no incluye** el escudo ni la marca gráfica del Ayuntamiento de Gijón. La
identidad del producto está centralizada en `src/brand.ts` y se representa con el monograma del
favicon. Si un despliegue quiere mostrar la imagen institucional, debe incorporarla en su propia
personalización y con la autorización de uso de marca correspondiente: distribuir un logotipo
oficial en un repositorio público bajo una licencia de software libre daría a entender que la
marca se licencia con el código, y no es así.
