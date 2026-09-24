export default {
  'users.title': 'Usuarios',
  'users.subtitle': 'Personas con acceso a la plataforma en tu organización.',
  'users.count': '{count} en total',
  'users.new': 'Nuevo usuario',
  'users.search': 'Buscar por nombre o correo',
  'users.you': 'tú',

  'users.mask': 'Ocultar datos personales',
  'users.mask.on':
    'Los nombres y correos se muestran ofuscados. Desactívalo solo cuando necesites identificar a alguien.',
  'users.mask.off': 'Se muestran los datos personales completos.',

  'users.kpi.total': 'Usuarios',
  'users.kpi.active': 'Activos',
  'users.kpi.mfa': 'Con verificación en dos pasos',

  'users.col.user': 'Usuario',
  'users.col.role': 'Rol',
  'users.col.status': 'Estado',
  'users.col.mfa': 'Verificación en dos pasos',
  'users.col.lastActivity': 'Última actividad',
  'users.col.actions': 'Acciones',
  'users.actions': 'Acciones sobre {name}',

  'users.role.orgAdmin': 'Administración de la organización',
  'users.role.superAdmin': 'Administración de la plataforma',
  'users.role.qcAdmin': 'Control de calidad',
  'users.role.member': 'Usuario',

  'users.status.active': 'Activo',
  'users.status.disabled': 'Desactivado',
  'users.mfa.on': 'Activa',
  'users.mfa.off': 'No activa',

  'users.empty': 'Todavía no hay usuarios en la organización.',
  'users.emptySearch': 'Ningún usuario coincide con la búsqueda.',
  'users.forbidden': 'Solo quien administra la organización puede gestionar sus usuarios.',
  'users.loadFailed': 'No se han podido cargar los usuarios.',
  'users.actionFailed': 'No se ha podido completar la acción. Inténtalo de nuevo.',

  'users.create.title': 'Nuevo usuario',
  'users.create.help':
    'La persona recibirá un correo para elegir su contraseña. Hasta entonces no podrá entrar.',
  'users.create.name': 'Nombre y apellidos',
  'users.create.email': 'Correo electrónico',
  'users.create.submit': 'Crear usuario',
  'users.create.nameRequired': 'Indica el nombre.',
  'users.create.emailRequired': 'Indica el correo electrónico.',
  'users.create.emailInvalid': 'El correo electrónico no es válido.',
  'users.create.duplicate': 'Ya existe un usuario con ese correo electrónico.',
  'users.create.failed': 'No se ha podido crear el usuario.',
  'users.create.done': 'Usuario creado. Le hemos enviado el correo para elegir su contraseña.',
  'users.create.doneNoMail':
    'Usuario creado, pero el correo no ha salido. Reenvíalo desde el menú de acciones.',

  'users.password.action': 'Enviar correo de contraseña',
  'users.password.done': 'Correo enviado.',
  'users.password.failed': 'No se ha podido enviar el correo.',

  'users.disable.action': 'Desactivar',
  'users.disable.title': 'Desactivar usuario',
  'users.disable.text': '{name} no podrá iniciar sesión hasta que vuelvas a activarlo.',
  'users.disable.confirm': 'Desactivar',
  'users.disable.done': 'Usuario desactivado.',
  'users.enable.action': 'Activar',
  'users.enable.done': 'Usuario activado.',

  'users.delete.action': 'Eliminar',
  'users.delete.title': 'Eliminar usuario',
  'users.delete.text':
    'Se eliminará la cuenta de {name} y sus recursos propios. Esta acción no se puede deshacer.',
  'users.delete.confirm': 'Eliminar',
  'users.delete.done': 'Usuario eliminado.',
} as const
