export default {
  'accessibility.title': 'Declaración de accesibilidad',
  'accessibility.footerLink': 'Accesibilidad',

  'accessibility.intro':
    'Esta declaración se refiere a la Plataforma de Integración de Datos, la aplicación web de gestión del gemelo digital de afluencia. Se ha redactado conforme al Real Decreto 1112/2018, sobre accesibilidad de los sitios web y aplicaciones para dispositivos móviles del sector público.',

  'accessibility.compliance.title': 'Situación de cumplimiento',
  'accessibility.compliance.body':
    'La plataforma es parcialmente conforme con la norma UNE-EN 301 549:2019 y con las Pautas de Accesibilidad para el Contenido Web (WCAG) 2.1 en nivel AA. «Parcialmente conforme» significa que se cumple la mayor parte de los requisitos, pero no todos: a continuación se detalla el contenido que no los cumple y por qué.',

  'accessibility.nonAccessible.title': 'Contenido no accesible',
  'accessibility.nonAccessible.intro':
    'El contenido que sigue no es accesible por los motivos que se indican, todos ellos por falta de conformidad con el Real Decreto 1112/2018:',

  'accessibility.nonAccessible.tiles.title': 'Cartografía base de los mapas',
  'accessibility.nonAccessible.tiles.body':
    'La cartografía la sirve un proveedor externo en forma de imágenes, de modo que los nombres de calles y lugares no son texto y no se pueden leer con un lector de pantalla ni ampliar sin pérdida de nitidez. La plataforma no puede corregir el contenido de esas imágenes. Como alternativa equivalente, cada mapa ofrece una tabla con el nombre, el tipo y las coordenadas de todas las entidades visibles, que se actualiza con el encuadre y desde la que se llega al detalle de cada una. El lienzo del mapa, además, se desplaza con las flechas del teclado y se amplía con las teclas más y menos. El contraste de la cartografía se ha medido sobre los píxeles representados y alcanza al menos 8:1 en los niveles de ampliación de uso habitual, por encima del 4,5:1 exigido.',

  'accessibility.nonAccessible.charts.title': 'Gráficas de los paneles',
  'accessibility.nonAccessible.charts.body':
    'Las gráficas se dibujan sobre un lienzo y su contenido no forma parte de la estructura de la página. Cada una lleva nombre accesible y descripción textual, y los datos representados están disponibles en forma de tabla en la vista de series temporales, pero la lectura punto por punto sobre la propia gráfica no es posible con un lector de pantalla.',

  'accessibility.nonAccessible.scope.title': 'Alcance de la revisión',
  'accessibility.nonAccessible.scope.body':
    'La revisión ha cubierto las vistas y los componentes compartidos de la aplicación. No se ha revisado de forma exhaustiva cada combinación de configuración de panel ni cada plantilla de cuadro de mando, por lo que pueden existir problemas no detectados en configuraciones concretas.',

  'accessibility.preparation.title': 'Preparación de la declaración',
  'accessibility.preparation.body':
    'Esta declaración se preparó el {date}. El método empleado ha sido una autoevaluación posterior a una revisión de accesibilidad realizada por un tercero independiente, cuyos hallazgos se han corregido. La declaración se revisará cuando cambien las funcionalidades evaluadas.',

  'accessibility.feedback.title': 'Observaciones y datos de contacto',
  'accessibility.feedback.body':
    'Se pueden comunicar problemas de accesibilidad, solicitar información en un formato alternativo o presentar cualquier otra dificultad de acceso al contenido a través de la unidad responsable del organismo titular de la plataforma.',
  'accessibility.feedback.contact': 'Contacto para cuestiones de accesibilidad: {contact}',
  'accessibility.feedback.unset':
    'El organismo titular de esta instalación no ha configurado todavía la vía de contacto para cuestiones de accesibilidad. Debe indicarse antes de publicar la plataforma: es un contenido obligatorio de esta declaración.',

  'accessibility.enforcement.title': 'Procedimiento de aplicación',
  'accessibility.enforcement.body':
    'Si tras una comunicación o una solicitud de información accesible la respuesta no resulta satisfactoria, o no se recibe respuesta, puede presentarse una reclamación ante la unidad responsable de accesibilidad del organismo titular, para conocer y oponerse a los motivos de la desestimación, instar a la adopción de las medidas oportunas o exponer cualquier otra alegación.',
}
