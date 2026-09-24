export default {
  'preferences.title': 'Preferencias',
  'preferences.subtitle': 'Idioma, zona horaria, formatos, apariencia y seguridad de la cuenta.',

  'preferences.save': 'Guardar cambios',
  'preferences.discard': 'Descartar',
  'preferences.dirtyOne': 'Hay un cambio sin guardar.',
  'preferences.dirtyMany': 'Hay {count} cambios sin guardar.',
  'preferences.clean': 'No hay cambios pendientes.',
  'preferences.pendingTag': 'Sin guardar',

  'preferences.section.locale': 'Idioma y región',
  'preferences.section.locale.help':
    'El idioma de los textos que genera el servidor y la zona horaria con la que se leen las medidas.',
  'preferences.section.formats': 'Formatos',
  'preferences.section.formats.help':
    'Cómo se escriben las fechas y las cifras en las tablas, los paneles y las fichas.',
  'preferences.section.appearance': 'Apariencia',
  'preferences.section.appearance.help':
    'El tema se aplica al guardar, sin necesidad de recargar la página.',

  // El rotulo dice a que afecta el ajuste, no solo la nota de ayuda: llamarlo «Idioma» a secas
  // hacía esperar que cambiara la interfaz, que se sirve solo en español (ACC-005).
  'preferences.section.security': 'Seguridad',
  'preferences.section.security.help':
    'Protege el acceso con un segundo factor. Se aplica al instante, sin pulsar «Guardar cambios».',
  'preferences.field.activeMFA': 'Verificación en dos pasos por correo',
  'preferences.field.activeMFA.hint':
    'Al iniciar sesión, tras la contraseña, se pedirá un código de un solo uso enviado a {email}.',
  'preferences.mfa.enabled':
    'Verificación en dos pasos activada. Se pedirá el código a partir del próximo inicio de sesión.',
  'preferences.mfa.disabled': 'Verificación en dos pasos desactivada.',
  'preferences.mfa.failed': 'No se ha podido cambiar la verificación en dos pasos. Inténtalo de nuevo.',
  'preferences.mfa.forced':
    'Tu organización exige la verificación en dos pasos a todos sus usuarios y no permite desactivarla.',

  'preferences.field.language': 'Idioma de las notificaciones',
  'preferences.field.language.hint':
    'Idioma de los textos que genera el servidor, como los correos de aviso. La interfaz se muestra siempre en español.',
  'preferences.field.timeZone': 'Zona horaria',
  'preferences.field.timeZone.hint':
    'Las medidas se almacenan en UTC. Zona detectada en este navegador: {zone}.',
  'preferences.field.datetimeFormat': 'Formato de fecha',
  'preferences.field.numberFormat': 'Formato numérico',
  'preferences.field.displayskinMode': 'Tema',

  'preferences.language.es': 'Español',
  'preferences.language.en': 'Inglés',

  'preferences.datetimeFormat.esES': 'Día/mes/año (31/12/2025)',
  'preferences.datetimeFormat.enUS': 'Mes/día/año (12/31/2025)',
  'preferences.datetimeFormat.iso': 'ISO 8601 (2025-12-31)',

  'preferences.numberFormat.esES': 'Español (1.234,56)',
  'preferences.numberFormat.enEN': 'Inglés (1,234.56)',
  'preferences.unknownOption': 'Otro ({value})',

  'preferences.theme.light': 'Claro',
  'preferences.theme.dark': 'Oscuro',
  'preferences.theme.system': 'Automático',
  'preferences.theme.lightWord': 'claro',
  'preferences.theme.darkWord': 'oscuro',
  'preferences.theme.systemHint': 'Sigue la configuración del sistema, que ahora pide el tema {mode}.',

  'preferences.preview.title': 'Vista previa',
  'preferences.preview.help': 'Así se verán las fechas y las cifras con las opciones elegidas.',
  'preferences.preview.datetime': 'Fecha y hora',
  'preferences.preview.date': 'Fecha',
  'preferences.preview.time': 'Hora',
  'preferences.preview.relative': 'Tiempo relativo',
  'preferences.preview.number': 'Cifra',
  'preferences.preview.note': 'La vista previa usa la hora actual y una cifra de ejemplo.',

  'preferences.saved': 'Preferencias guardadas.',
  'preferences.partialSaved': 'Se han guardado {ok} de {total} preferencias.',
  'preferences.noneSaved': 'No se ha podido guardar ninguna preferencia.',
  'preferences.failedItem': '{label}: {reason}',
  'preferences.forced': 'Tu organización fija este ajuste y no permite cambiarlo.',

  'preferences.noSession': 'No hay ninguna sesión activa.',
  'preferences.reload': 'Volver a cargar',
} as const
