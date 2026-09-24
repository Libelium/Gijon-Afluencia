export default {
  'ontology.title': 'Ontología',
  'ontology.subtitle': 'Elementos de la plataforma según la ontología de turismo de SEGITTUR.',
  'ontology.loadFailed': 'No se ha podido cargar la ontología.',

  'ontology.meta.version': 'Versión {version}',
  'ontology.meta.classes': 'clases',
  'ontology.meta.properties': 'propiedades',
  'ontology.meta.schemes': 'tesauros',
  'ontology.meta.concepts': 'conceptos',
  'ontology.meta.source': 'Fuente:',

  'ontology.tab.mapping': 'Correspondencia con la plataforma',
  'ontology.tab.classes': 'Clases',
  'ontology.tab.schemes': 'Tesauros',

  'ontology.mapping.intro':
    'Cada punto de interés turístico (PIT) que monitoriza la plataforma se identifica con una clase de la ontología de SEGITTUR, y su aforo con la propiedad «aforo» (capacity). La ontología describe recursos turísticos, no sensores: las medidas siguen los Smart Data Models de FIWARE y se enlazan con el PIT por su zona.',
  'ontology.mapping.destination': 'Destino turístico',
  'ontology.mapping.site': 'Conjunto de interés',
  'ontology.mapping.pits': 'Puntos de interés turístico ({count})',
  'ontology.mapping.pitsHelp':
    'Zonas de aforo del despliegue y la clase de SEGITTUR con que se describe cada una.',
  'ontology.mapping.pitsCaption': 'Correspondencia de los puntos de interés turístico con las clases de SEGITTUR',
  'ontology.mapping.pitProperties': 'Propiedades de SEGITTUR de cada PIT',
  'ontology.mapping.related': 'Otros recursos relacionados',
  'ontology.mapping.measurements': 'Medidas y dispositivos (FIWARE)',
  'ontology.mapping.measurementsHelp':
    'Entidades que publica la plataforma sobre cada PIT y cómo se relacionan con su descripción en SEGITTUR.',

  'ontology.col.pit': 'Punto de interés',
  'ontology.col.zone': 'Zona',
  'ontology.col.class': 'Clase SEGITTUR',
  'ontology.col.property': 'Propiedad',
  'ontology.col.kind': 'Tipo',
  'ontology.col.range': 'Valor',
  'ontology.col.from': 'Definida en',
  'ontology.col.datamodel': 'Modelo de datos',
  'ontology.col.content': 'Contenido',
  'ontology.col.relation': 'Relación con SEGITTUR',

  'ontology.kind.datatype': 'Dato',
  'ontology.kind.object': 'Relación',

  'ontology.classes.search': 'Buscar clase',
  'ontology.classes.results': 'Clases encontradas',
  'ontology.classes.noResults': 'Ninguna clase coincide con la búsqueda.',
  'ontology.classes.tree': 'Jerarquía de clases',
  'ontology.tree.expand': 'Desplegar {name}',
  'ontology.tree.collapse': 'Plegar {name}',
  'ontology.tree.usedHint': 'Usada por la plataforma',
  'ontology.tree.legend': 'Clases que usa la plataforma',

  'ontology.detail.hierarchy': 'Jerarquía',
  'ontology.detail.external': 'Se abre en una pestaña nueva',
  'ontology.detail.noComment': 'La ontología no incluye descripción para esta clase.',
  'ontology.detail.usedBy': 'La usan {count} puntos de interés de la plataforma',
  'ontology.detail.usedByOne': 'La usa 1 punto de interés de la plataforma',
  'ontology.detail.subclasses': 'Subclases ({count})',
  'ontology.detail.properties': 'Propiedades aplicables ({count})',
  'ontology.detail.propertiesCaption': 'Propiedades aplicables a {name}',
  'ontology.detail.noProperties': 'No tiene propiedades propias ni heredadas.',
  'ontology.detail.own': 'Esta clase',

  'ontology.schemes.help':
    'Vocabularios controlados (SKOS) con los valores admitidos por la ontología: tipos de destino, de servicio, de evento, etc.',
  'ontology.schemes.search': 'Buscar en los tesauros',
  'ontology.schemes.noResults': 'Ningún tesauro ni concepto coincide con la búsqueda.',
  'ontology.schemes.count': '{count} conceptos',
} as const
