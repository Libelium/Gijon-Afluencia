/**
 * Contenido de la ayuda de la aplicacion.
 *
 * Va en codigo y no en el servidor: describe estas pantallas, cambia con ellas y se revisa en el
 * mismo cambio. El texto de interfaz (rotulos, buscador) vive en `i18n.ts`; esto es el cuerpo.
 */

export interface HelpLink {
  label: string
  to?: string
  href?: string
}

export interface HelpSection {
  id: string
  title: string
  icon: string
  paragraphs: string[]
  items?: { term: string; text: string }[]
  links?: HelpLink[]
}

export interface FaqEntry {
  question: string
  answer: string
}

export const SECTIONS: HelpSection[] = [
  {
    id: 'primeros-pasos',
    title: 'Primeros pasos',
    icon: 'mdi-rocket-launch-outline',
    paragraphs: [
      'La Plataforma de Integración de Datos del Ayuntamiento de Gijón reúne los datos de los sensores de aforo y de flujo de personas del municipio para analizar la afluencia en los puntos de interés turístico (PIT).',
      'El acceso se hace con el usuario y la contraseña de la organización en la pantalla de inicio de sesión. Al terminar, la sesión se cierra desde el menú del avatar, arriba a la derecha.',
      'Para proteger la cuenta con un segundo factor, activa la verificación en dos pasos en Preferencias → Seguridad. A partir del siguiente acceso, después de la contraseña se pedirá un código de un solo uso enviado a tu correo.',
    ],
    links: [{ label: 'Ir a Preferencias', to: '/preferencias' }],
  },
  {
    id: 'entidades',
    title: 'Entidades',
    icon: 'mdi-access-point',
    paragraphs: [
      'Una entidad es cada fuente de datos de la plataforma: un sensor LIDAR que cuenta y clasifica personas en una zona, o un dispositivo SmartSpot que detecta la presencia de visitantes.',
      'El listado se puede buscar por nombre o identificador y filtrar por modelo de datos y espacio de datos. La ficha de cada entidad muestra su identidad, su ubicación en un mapa, las medidas actuales con la hora de su última actualización y el histórico de cada medida en el rango de fechas que elijas.',
    ],
    links: [{ label: 'Ir a Entidades', to: '/entidades' }],
  },
  {
    id: 'mapa',
    title: 'Mapa',
    icon: 'mdi-map-outline',
    paragraphs: [
      'El mapa muestra la red de sensores desplegada en el municipio: cada marcador es una entidad con ubicación. Se puede filtrar por modelo de datos y buscar una entidad concreta; al desplazar o acercar el mapa se actualizan las entidades del área visible.',
      'Las mismas entidades del área visible se pueden consultar en forma de tabla. Con el foco en el mapa, las flechas lo desplazan y las teclas + y − cambian el zoom.',
    ],
    links: [{ label: 'Ir al Mapa', to: '/mapa' }],
  },
  {
    id: 'paneles',
    title: 'Paneles',
    icon: 'mdi-view-dashboard-outline',
    paragraphs: [
      'Los paneles agrupan gráficas sobre los datos de los sensores. Cada gráfica tiene su selector de rango de fechas y una tabla con los mismos datos para quien no pueda o no quiera leer la gráfica. Las plantillas disponibles son:',
    ],
    items: [
      { term: 'Aforo Monitorización', text: 'Ocupación por punto de medida, con mapa, evolución temporal y reparto por franjas.' },
      { term: 'Aforo Clasificación', text: 'Reparto de personas por categoría detectada, con evolución y totales.' },
      { term: 'Clasificación Avanzada', text: 'Clasificación con comparativa entre puntos, franjas horarias y acumulados.' },
      { term: 'Aforo Mapa de Calor', text: 'Intensidad de ocupación por hora y día de la semana, y mapa de densidad sobre los puntos de interés turístico.' },
      { term: 'Aforo Tránsitos', text: 'Desplazamientos de personas entre puntos de medida, con origen, destino y volumen.' },
      { term: 'Tránsitos avanzado', text: 'Tránsitos con matriz origen-destino, rutas principales y evolución.' },
      { term: 'Zona LIDAR Analítica', text: 'Indicadores de la zona LIDAR: ocupación, aforo, permanencia y series históricas.' },
      { term: 'Zona LIDAR Mapa de calor', text: 'Densidad de ocupación en vivo sobre la zona monitorizada.' },
      { term: 'Zona LIDAR Predicción', text: 'Ocupación prevista frente a la medida, con banda de confianza: la proyección a futuro del aforo.' },
    ],
    links: [{ label: 'Ir a Paneles', to: '/paneles' }],
  },
  {
    id: 'alarmas',
    title: 'Alarmas',
    icon: 'mdi-bell-outline',
    paragraphs: [
      'Una alarma vigila los datos de uno o varios sensores y avisa cuando se cumple su condición. Hay dos tipos de condición: de umbral, cuando una medida supera o baja de un valor, y de inactividad, cuando un sensor deja de enviar datos durante más tiempo del configurado.',
      'Cada alarma tiene sus avisos: correo electrónico, mensaje SMS, notificación en la aplicación o llamada a un servicio externo, según los canales configurados en la organización. Su estado puede ser Activa (habilitada y en reposo), Disparada (la condición se cumple ahora) o Desactivada (no se evalúa ni envía avisos). La ficha de cada alarma guarda su histórico de estado de los últimos 30 días.',
    ],
    links: [
      { label: 'Ir a Alarmas', to: '/alarmas' },
      { label: 'Crear una alarma', to: '/alarmas/nueva' },
    ],
  },
  {
    id: 'preferencias',
    title: 'Preferencias',
    icon: 'mdi-tune-variant',
    paragraphs: [
      'Ajustes personales de tu cuenta: el idioma de las notificaciones que genera el servidor (como los correos de aviso), la zona horaria con la que se leen las medidas, el formato de fechas y cifras, y el tema de la interfaz: claro, oscuro o automático según el sistema.',
      'En la tarjeta Seguridad se activa o desactiva la verificación en dos pasos por correo. Si la organización la exige a todos sus usuarios, el ajuste aparece bloqueado.',
    ],
    links: [{ label: 'Ir a Preferencias', to: '/preferencias' }],
  },
  {
    id: 'personalizacion',
    title: 'Personalización',
    icon: 'mdi-palette-outline',
    paragraphs: [
      'La imagen de la organización: colores de marca (con la comprobación de contraste AA sobre los temas claro y oscuro), logotipos para el tema claro, el tema oscuro y la pantalla de inicio de sesión, y el pie de página, donde se colocan los logotipos de financiación.',
      'Cada organización tiene su propia personalización, así que la misma plataforma puede servir a otros ayuntamientos con su identidad visual sin tocar el código.',
    ],
    links: [{ label: 'Ir a Personalización', to: '/personalizacion' }],
  },
  {
    id: 'usuarios',
    title: 'Usuarios',
    icon: 'mdi-account-group-outline',
    paragraphs: [
      'La gestión de usuarios de la organización permite dar de alta cuentas nuevas, activarlas o desactivarlas y enviar el correo para restablecer la contraseña. Los datos personales (nombre y correo) aparecen ocultos por defecto y solo se muestran cuando se pide expresamente.',
    ],
    links: [{ label: 'Ir a Usuarios', to: '/usuarios' }],
  },
  {
    id: 'api',
    title: 'API',
    icon: 'mdi-api',
    paragraphs: [
      'La plataforma expone dos API documentadas con OpenAPI: la de gestión, para consultar entidades, series temporales, paneles y alarmas con un token de Keycloak, y la de ingesta, por la que entran los datos de los dispositivos. La pantalla API muestra todos sus endpoints y permite descargar la especificación.',
    ],
    links: [{ label: 'Ver la API', to: '/api' }],
  },
  {
    id: 'accesibilidad',
    title: 'Accesibilidad',
    icon: 'mdi-human',
    paragraphs: [
      'La aplicación se ha diseñado para cumplir las pautas WCAG 2.1 de nivel AA: se puede usar entera con teclado, las gráficas tienen su tabla de datos equivalente y los colores respetan el contraste mínimo. La declaración de accesibilidad recoge el estado de cumplimiento y cómo comunicar un problema.',
    ],
    links: [{ label: 'Declaración de accesibilidad', to: '/accesibilidad' }],
  },
  {
    id: 'soporte',
    title: 'Soporte',
    icon: 'mdi-lifebuoy',
    paragraphs: [
      'Para cualquier incidencia, duda o petición sobre la plataforma, escribe al buzón de soporte indicando la pantalla, qué intentabas hacer y, si puedes, una captura.',
    ],
    links: [{ label: 'soportepidgijon@gijon.es', href: 'mailto:soportepidgijon@gijon.es' }],
  },
]

export const FAQ: FaqEntry[] = [
  {
    question: 'No me llega el código de verificación',
    answer:
      'Revisa la carpeta de correo no deseado y espera un minuto: el envío puede tardar. El código caduca a los pocos minutos; si ha caducado, vuelve a iniciar sesión para recibir uno nuevo. Si sigue sin llegar, escribe a soporte para que comprueben tu dirección de correo.',
  },
  {
    question: '¿Cómo cambio entre tema claro y oscuro?',
    answer:
      'Con el botón del sol o la luna de la barra superior, al momento, o en Preferencias → Apariencia, donde además puedes elegir «Automático» para seguir el tema del sistema.',
  },
  {
    question: 'No veo un sensor en el mapa',
    answer:
      'El mapa solo muestra las entidades con ubicación dentro del área visible. Reduce el zoom, quita los filtros o usa «Ver dónde hay datos». Si la entidad no publica su ubicación, aparece en el listado de Entidades pero no en el mapa.',
  },
  {
    question: '¿Cómo creo una alarma?',
    answer:
      'En Alarmas → Nueva alarma: elige la entidad y la medida, define la condición (umbral o inactividad) y añade los avisos que quieres recibir, por ejemplo un correo electrónico o un SMS.',
  },
  {
    question: 'Una gráfica sale vacía',
    answer:
      'Significa que no hay datos en el rango de fechas elegido. Amplía el rango con el selector de la gráfica o comprueba en la ficha de la entidad cuándo llegó su último dato.',
  },
  {
    question: '¿Por qué las horas no coinciden con las de mi reloj?',
    answer:
      'Las medidas se guardan en UTC y se muestran en la zona horaria de tus preferencias. Cámbiala en Preferencias → Idioma y región.',
  },
  {
    question: '¿Puedo leer los datos de una gráfica sin verla?',
    answer:
      'Sí. Cada gráfica tiene el botón «Ver los datos en una tabla», que muestra los mismos valores en una tabla accesible con lector de pantalla.',
  },
]
