export default {
  'apiDocs.title': 'API de la plataforma',
  'apiDocs.subtitle': 'Referencia de las API de gestión y de ingesta, generada desde su especificación OpenAPI.',
  'apiDocs.tabs': 'API disponibles',
  'apiDocs.tab.gestion': 'Gestión',
  'apiDocs.tab.ingesta': 'Ingesta',
  'apiDocs.download': 'Descargar especificación',
  'apiDocs.loadError': 'No se ha podido cargar la especificación.',
  'apiDocs.version': 'Versión {version}',

  'apiDocs.auth': 'Autenticación',
  'apiDocs.auth.gestion':
    'Token JWT de tipo bearer emitido por Keycloak (flujo de código con PKCE). Se envía en la cabecera Authorization de cada petición.',
  'apiDocs.auth.ingesta':
    'Sin JWT. Cada dispositivo se identifica con su apikey en el parámetro «k» de la petición; el webhook LIDAR se protege con un secreto compartido.',
  'apiDocs.servers': 'Servidores',

  'apiDocs.search': 'Buscar por ruta, método o descripción',
  'apiDocs.count': '{count} endpoints',
  'apiDocs.countOne': '1 endpoint',
  'apiDocs.noResults': 'Ningún endpoint coincide con la búsqueda.',

  'apiDocs.parameters': 'Parámetros',
  'apiDocs.parameters.none': 'Sin parámetros.',
  'apiDocs.parameters.caption': 'Parámetros de {path}',
  'apiDocs.col.name': 'Nombre',
  'apiDocs.col.in': 'Ubicación',
  'apiDocs.col.type': 'Tipo',
  'apiDocs.col.required': 'Obligatorio',
  'apiDocs.col.description': 'Descripción',
  'apiDocs.yes': 'Sí',
  'apiDocs.no': 'No',

  'apiDocs.body': 'Cuerpo de la petición',
  'apiDocs.body.free': 'Objeto libre: el esquema no fija sus propiedades.',
  'apiDocs.required': 'obligatorio',
  'apiDocs.optional': 'opcional',
  'apiDocs.schema.truncated': 'estructura anidada omitida',
  'apiDocs.responses': 'Respuestas',
} as const
