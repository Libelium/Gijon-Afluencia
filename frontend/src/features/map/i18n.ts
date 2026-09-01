export default {
  'map.title': 'Mapa',
  'map.subtitle': 'Entidades localizadas en el área visible',

  'map.search': 'Buscar entidad',
  'map.datamodel': 'Modelo de datos',
  'map.noDatamodels': 'No hay modelos de datos disponibles',
  'map.filters': 'Buscador y filtros',
  'map.showFilters': 'Mostrar buscador y filtros',
  'map.hideFilters': 'Ocultar buscador y filtros',
  'map.filtersApply': 'Ver el mapa',
  'map.clearFilters': 'Quitar filtros',
  'map.loading': 'Buscando entidades…',

  'map.count.zero': 'Sin entidades en esta zona',
  'map.count.one': '1 entidad en esta zona',
  'map.count.many': '{n} entidades en esta zona',
  'map.count.capped': '{n} de {total} entidades en esta zona',
  // Version corta para la barra flotante en movil, donde no cabe la frase completa.
  'map.count.zeroShort': 'Sin entidades',
  'map.count.oneShort': '1 entidad',
  'map.count.manyShort': '{n} entidades',
  'map.count.cappedShort': '{n} de {total} entidades',
  'map.withoutLocation': 'Hay {n} entidades sin ubicación que el mapa no puede mostrar.',
  'map.withoutLocationOne': 'Hay 1 entidad sin ubicación que el mapa no puede mostrar.',

  'map.locateData': 'Ver dónde hay datos',
  'map.locating': 'Buscando dónde hay datos…',
  'map.locateEmpty': 'No se ha encontrado ninguna entidad con ubicación.',

  'map.empty': 'No hay entidades en esta zona. Desplaza el mapa o reduce el zoom para ampliar el área.',
  'map.emptyFiltered': 'Ningún resultado en esta zona con los filtros aplicados.',

  'map.identifier': 'Identificador',
  'map.coordinates': 'Latitud y longitud',
  'map.viewDetail': 'Ver detalle',

  // Alternativa por teclado y por texto del mapa (WCAG 1.1.1 y 2.1.1).
  'map.table.toggle': 'Ver en una tabla las {n} entidades del área visible',
  'map.table.toggleOne': 'Ver en una tabla la entidad del área visible',
  'map.table.toggleEmpty': 'Ver en una tabla las entidades del área visible',
  'map.table.caption':
    'Entidades del área visible del mapa. La lista se actualiza al desplazar o ampliar el mapa.',
  'map.table.name': 'Entidad',
  'map.table.datamodel': 'Modelo de datos',
  'map.table.coordinates': 'Latitud y longitud',
  'map.mapLabel': 'Mapa de entidades. Con el foco puesto en él, las flechas lo desplazan y las teclas + y − cambian el zoom.',
} as const
