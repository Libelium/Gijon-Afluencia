export default {
  'customization.title': 'Personalización',
  'customization.subtitle':
    'Colores, logotipos y pie de página de la organización. Se aplican a todo el mundo que entra.',

  'customization.section.colors': 'Colores de marca',
  'customization.section.colors.help':
    'Se indica un color por papel y la aplicación calcula las variantes de tema claro y oscuro con el contraste que exige la normativa de accesibilidad. Al pie de cada campo se indica el contraste obtenido.',
  'customization.section.logos': 'Logotipos',
  'customization.section.logos.help':
    'PNG, JPEG, WebP o GIF, hasta 512 KB. No se admite SVG por seguridad. Si no subes ninguno se muestran las iniciales sobre el color primario.',
  'customization.section.footer': 'Pie de página',
  'customization.section.footer.help':
    'HTML sencillo: texto, enlaces e imágenes. Se limpia en el servidor y otra vez al pintarlo, así que las etiquetas ejecutables se descartan.',

  'customization.field.themePrimaryColor': 'Color primario',
  'customization.field.themePrimaryColor.hint':
    'Botones, enlaces y elementos activos. Es el color que más se ve.',
  'customization.field.themeSecondaryColor': 'Color secundario',
  'customization.field.themeSecondaryColor.hint': 'Acciones de apoyo y elementos de segundo plano.',
  'customization.field.themeLightPrimaryColor': 'Color de acento',
  'customization.field.themeLightPrimaryColor.hint':
    'Avisos informativos y detalles gráficos. Admite menos contraste porque no lleva texto encima.',

  'customization.field.themeLightIcon': 'Logotipo, tema claro',
  'customization.field.themeLightIcon.hint': 'Se muestra en la barra lateral con el tema claro.',
  'customization.field.themeDarkIcon': 'Logotipo, tema oscuro',
  'customization.field.themeDarkIcon.hint':
    'La variante que se lee sobre fondo oscuro, normalmente en blanco. Si no la subes se reutiliza la del tema claro.',
  'customization.field.themeLoginIcon': 'Logotipo de inicio de sesión',
  'customization.field.themeLoginIcon.hint':
    'Lo recoge Keycloak para su página de inicio de sesión, donde va sobre un degradado hecho con los colores de marca. Sube la variante en claro (normalmente en blanco): la versión a color se perdería sobre ese fondo. La pantalla de acceso de la aplicación no usa este campo, sino los dos logotipos de arriba.',
  'customization.field.themeCustomFooter': 'Contenido del pie',

  'customization.color.contrast': 'Contraste {ratio}:1 sobre {surface}',
  'customization.color.light': 'claro',
  'customization.color.dark': 'oscuro',
  'customization.color.pass': 'Cumple AA',
  'customization.color.fail': 'No cumple AA',
  'customization.color.adjusted':
    'Sobre fondo oscuro se aclara automáticamente a {value} para llegar al contraste mínimo.',
  'customization.color.invalid': 'Escribe un color en hexadecimal, por ejemplo #97233F.',

  'customization.image.choose': 'Elegir imagen',
  'customization.image.replace': 'Sustituir',
  'customization.image.remove': 'Quitar',
  'customization.image.none': 'Sin imagen',
  'customization.image.tooLarge': 'La imagen pesa {size} y el máximo son 512 KB.',
  'customization.image.badType': 'Formato no admitido. Usa PNG, JPEG, WebP o GIF.',
  'customization.image.isSvg': 'No se admite SVG: puede llevar código ejecutable dentro.',

  'customization.footer.placeholder':
    '<p>Texto del pie, con <a href="https://ejemplo.org">enlaces</a> si hace falta.</p>',
  'customization.footer.preview': 'Vista previa',
  'customization.footer.previewEmpty': 'Sin pie de página.',
  'customization.footer.imageHint':
    'Para insertar una imagen, súbela con el botón: se incrusta en el HTML como una línea larga de base64 que no hace falta leer. Revisa el resultado en la vista previa de abajo. El atributo «style» solo se conserva en span, div, img y figure: para centrar, envuelve en <div style="text-align:center">.',
  'customization.footer.insertImage': 'Insertar imagen',
  'customization.footer.stripImages': 'Quitar las imágenes',
  'customization.footer.embedded': '{count} imagen(es) incrustada(s) · {size} KB en total',

  'customization.save': 'Guardar cambios',
  'customization.discard': 'Descartar',
  'customization.saved': 'Personalización guardada.',
  'customization.reset': 'Volver al valor por defecto',
  'customization.dirtyOne': 'Hay un cambio sin guardar.',
  'customization.dirtyMany': 'Hay {count} cambios sin guardar.',
  'customization.clean': 'No hay cambios pendientes.',
  'customization.pendingTag': 'Sin guardar',

  'customization.preview.title': 'Cómo queda',
  'customization.preview.help':
    'Los colores se aplican a la interfaz en cuanto se guardan, sin recargar la página.',
  'customization.preview.button': 'Acción principal',
  'customization.preview.secondary': 'Acción secundaria',
  'customization.preview.chip': 'Etiqueta',
  'customization.preview.link': 'Un enlace',

  'customization.noOrganization':
    'Tu usuario no pertenece a ninguna organización, así que no hay nada que personalizar.',
  'customization.forbidden': 'No tienes permiso para cambiar la personalización de la organización.',
}
