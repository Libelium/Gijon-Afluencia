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
      'Aforo máximo de una zona: en la ficha de una zona de afluencia, quien la administra o tiene acceso de «Edición» tiene el botón «Aforo máximo», junto a «Renombrar». Se escribe en personas y se guarda en la propia zona; también se puede quitar. Es el aforo con el que los paneles calculan qué parte de la zona está ocupada: sin él, la zona no se colorea en el mapa de calor de zonas y sus porcentajes no aparecen.',
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
      {
        term: 'Aforo Monitorización',
        text: 'Ocupación por punto de medida, con mapa, evolución temporal y reparto por franjas. A esta plantilla, a las de clasificación y al mapa de calor se les asigna la entidad de eventos de cada sensor de conteo WiFi/BLE, la de «Visitas y recorridos» que termina en _CFE: su aforo son las personas distintas detectadas en cada intervalo, repartidas en turistas, residentes y visitantes de corta estancia. El selector la ofrece la primera, y el mapa la sitúa en la ubicación de su sensor.',
      },
      { term: 'Aforo Clasificación', text: 'Reparto de personas por categoría detectada, con evolución y totales.' },
      { term: 'Clasificación Avanzada', text: 'Clasificación con comparativa entre puntos, franjas horarias y acumulados.' },
      { term: 'Aforo Mapa de Calor', text: 'Intensidad de ocupación por hora y día de la semana, y mapa de densidad sobre los puntos de interés turístico.' },
      {
        term: 'Aforo Tránsitos',
        text: 'Personas que un sensor de conteo WiFi/BLE detecta y que después aparecen en otro, con origen, destino y volumen por hora. Asigna al menos dos sensores: su entidad de «Visitas y recorridos» (la que termina en _CFE) o la de «Conteos WiFi/BLE (por sensor)» (la que termina en _CFO), que además los sitúa en el mapa. Las zonas LIDAR y las zonas de aforo no sirven para esta plantilla.',
      },
      { term: 'Tránsitos avanzado', text: 'Lo mismo, con matriz origen-destino, rutas principales y evolución. Se asignan las mismas entidades.' },
      {
        term: 'Zona LIDAR Analítica',
        text: 'Indicadores de la zona LIDAR: ocupación, aforo, permanencia y series históricas. La evolución de la ocupación marca las horas anómalas (ver Anomalías).',
      },
      { term: 'Zona LIDAR Mapa de calor', text: 'Densidad de ocupación en vivo sobre la zona monitorizada.' },
      {
        term: 'Zona Mapa de coropletas',
        text: 'Mapa de calor con cada zona coloreada según el porcentaje de su aforo máximo que está ocupado, de verde (vacía) a rojo oscuro (llena), con sus LIDAR y sus sensores WiFi/BLE encima. La ocupación es la cifra de la zona que combina los dos tipos de sensor. Muestra la de ahora y, con la barra, la media de cada hora o de cada día del rango elegido; al reproducirla, los cambios de color muestran cómo sube y baja la gente. Se asignan las zonas de afluencia. Solo se colorean las que tienen como ubicación el contorno de la zona y un aforo máximo; las demás siguen en la lista de debajo del mapa con su ocupación. El aforo máximo se pone en la ficha de cada zona (ver Entidades).',
      },
      {
        term: 'Zona LIDAR Predicción',
        text: 'Ocupación prevista frente a la medida, con banda de confianza: la proyección a futuro del aforo. Incluye un simulador de escenarios: se añaden uno o varios eventos (tipo, hora, duración, meteorología e intensidad) y se ve cómo cambiaría la ocupación prevista de la zona y si superaría su aforo. Sus cifras son orientativas, para comparar escenarios, y solo llegan hasta donde llega la previsión. Los eventos del registro de eventos de la plataforma salen ya como «Registrado» y se suman siempre: la previsión es la de un día normal, porque el modelo no aprende de los días con evento.',
      },
    ],
    links: [{ label: 'Ir a Paneles', to: '/paneles' }],
  },
  {
    id: 'anomalias',
    title: 'Anomalías',
    icon: 'mdi-alert-decagram-outline',
    paragraphs: [
      'Una hora anómala es una hora en la que la ocupación de una zona de afluencia es muy distinta de la habitual, o cambia de golpe de una hora a la siguiente. La plataforma las busca sola, una vez al día, de madrugada, sobre los días ya terminados: lo que pase hoy se marca mañana.',
      'Para decidir, compara cada hora con lo que ha aprendido de las anteriores: cuánta gente suele haber en las zonas a esa hora y ese día de la semana, y cuánto suele cambiar la ocupación de una hora a la siguiente. No hay un número fijo de personas a partir del cual algo sea anómalo, y lo aprendido se va poniendo al día. Lo que marca como anómalo no lo aprende, para no acostumbrarse a ello; pero si un cambio se mantiene tres horas seguidas, empieza a tomarlo como lo nuevo normal.',
      'Se ve en el panel «Zona LIDAR Analítica» y en los gráficos de líneas propios con la ocupación de una zona: son los puntos de la serie «Anomalía», sobre la ocupación. Con rangos de más de un mes la gráfica va por días, y un día sale marcado si lo está alguna de sus horas. En la ficha de la zona, la medida «Hora anómala» vale 1 en una hora anómala y 0 en una normal.',
      'Lo habitual se aprende de todas las zonas juntas. Por eso una zona mucho más concurrida que las demás puede salir marcada en sus horas punta, aunque para ella sean normales.',
    ],
    items: [
      {
        term: 'Un pico de una hora',
        text: 'Un concierto improvisado llena la plaza a las 18:00 y a las 19:00 ya está como siempre. Salen marcadas las 18:00 y también las 19:00 y las 20:00: la plataforma mira cuánto ha variado la ocupación en las dos horas anteriores, y el pico sigue dentro de esa ventana hasta las 20:00.',
      },
      {
        term: 'Un mercado de toda la semana',
        text: 'Un mercadillo navideño duplica la gente de 11:00 a 23:00 durante siete días. Cada día salen marcadas sobre todo las horas en que arranca y en que termina, cuando la ocupación cambia de golpe. Las del medio, con la plaza llena pero estable, casi nunca. La detección no consulta el registro de eventos: un evento registrado cuenta como cualquier otro cambio.',
      },
      {
        term: 'Un martes cualquiera',
        text: 'Una calle con poca gente un martes a las 8:00, como todos los martes: no sale nada. Que haya poca gente no es anómalo si a esa hora siempre hay poca.',
      },
      {
        term: 'Horas sin datos',
        text: 'Si una zona se queda unas horas sin datos, esas horas no se marcan ni como normales ni como anómalas: en la gráfica no aparece nada.',
      },
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
      'Cada usuario tiene un nivel de acceso a los datos de la organización. Con «Consulta» ve todas las entidades, el mapa, los paneles y las alarmas; con «Edición» además puede crear y modificar paneles y alarmas, y cambiar el nombre de las entidades y el aforo máximo de las zonas (el resto de datos de una entidad, como su ubicación, solo lo cambia quien administra); «Sin acceso» deja solo lo que el propio usuario haya creado. Los paneles y alarmas nuevos llegan solos a quien tenga nivel. Quien administra la organización lo ve y lo gestiona todo.',
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
    id: 'ontologia',
    title: 'Ontología',
    icon: 'mdi-graph-outline',
    paragraphs: [
      'Los elementos de la plataforma se describen con la ontología de referencia de turismo de SEGITTUR, la que usan las Plataformas Inteligentes de Destino. Cada punto de interés turístico (PIT) corresponde a una clase de la ontología —plaza, iglesia, ruta, recurso histórico— y su aforo a la propiedad «aforo» (capacity); Gijón es el destino turístico al que pertenecen.',
      'La pantalla Ontología muestra esa correspondencia, permite recorrer todas las clases con sus propiedades y consultar los tesauros de valores. La ontología no modela sensores: las medidas siguen los Smart Data Models de FIWARE y se enlazan con cada PIT por su zona.',
    ],
    links: [{ label: 'Ver la ontología', to: '/ontologia' }],
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
    question: '¿Cómo cambio el aforo máximo de una zona?',
    answer:
      'En Entidades, abre la zona de afluencia y pulsa «Aforo máximo», arriba a la derecha de su ficha. Escribe cuántas personas caben en la zona y guarda; con «Quitar el aforo» la zona se queda sin él. El valor nuevo puede tardar unos segundos en verse entre sus medidas. El botón solo aparece en las zonas, a quien administra la organización y a los usuarios con acceso de «Edición».',
  },
  {
    question: 'El mapa de calor de zonas no colorea una zona',
    answer:
      'Para colorearla, la zona necesita su contorno como ubicación y un aforo máximo: el color es su ocupación sobre ese aforo. Si el aviso del panel dice que hay zonas sin aforo máximo, ponlo en la ficha de cada una con «Aforo máximo». Si el problema es el contorno, la zona aparece en la lista de debajo del mapa marcada como «sin polígono».',
  },
  {
    question: 'Una gráfica sale vacía',
    answer:
      'Significa que no hay datos en el rango de fechas elegido. Amplía el rango con el selector de la gráfica o comprueba en la ficha de la entidad cuándo llegó su último dato.',
  },
  {
    question: 'No veo ninguna anomalía',
    answer:
      'Puede que no haya ninguna en el rango elegido; que el rango sea solo de hoy, que se revisa de madrugada al día siguiente; o que la detección de anomalías no esté activada en esta instalación. La serie «Anomalía» solo aparece en la leyenda cuando hay al menos una.',
  },
  {
    question: 'El panel de tránsitos sale vacío',
    answer:
      'La plataforma calcula los tránsitos cada hora y solo cuenta a quien dos sensores detectan dentro de la misma hora, así que con pocos visitantes o con sensores alejados puede no haber datos. Comprueba que el panel tiene al menos dos sensores de conteo WiFi/BLE (sus entidades terminadas en _CFE o _CFO; no las zonas LIDAR) y amplía el rango a 7 o 30 días.',
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
