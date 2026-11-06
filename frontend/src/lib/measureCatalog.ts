/**
 * Nombre en castellano y, si hace falta, descripcion de las medidas que publica la plataforma.
 *
 * El servidor da el nombre en ingles de los CSV de datamodels o, si la variable no esta en
 * ninguno (todas las de afluencia), el identificador con el camelCase separado. Lo que no esta
 * aqui conserva ese nombre. Las claves van en minusculas: las ETL de afluencia no son
 * consistentes (`touristaverageVisitDuration` y `shortTermVisitorAverageVisitDuration`).
 *
 * Solo lleva descripcion lo que se ha comprobado en el codigo que lo publica (predictions y las
 * ETL de afluencia del queues-consumer). Las variables sin productor en el repositorio, que en
 * pre vienen de datos de demostracion, se traducen pero no se describen.
 */

export interface MeasureInfo {
  name: string
  /** Solo cuando el nombre no basta: latitud o temperatura se explican solas. */
  description?: string
}

const VISIT =
  'Tiempo entre la primera y la última detección de una visita al sensor, en segundos.'
const TRANSIT =
  'Tiempo entre la última detección en el origen y la primera en el destino, en segundos.'
const STAY =
  'Tiempo que cada objeto está a la vista del LIDAR, en segundos. Solo cuenta a los que ya se han ido.'
const SMARTSPOT_COUNT = (minutes: string) =>
  `Dispositivos WiFi o Bluetooth distintos que el sensor ha detectado en su intervalo ${minutes}. Son dispositivos, no personas presentes a la vez.`

const MEASURES: Record<string, MeasureInfo> = {
  // Comunes
  name: { name: 'Nombre' },
  location: { name: 'Ubicación' },
  latitude: { name: 'Latitud' },
  longitude: { name: 'Longitud' },
  temperature: { name: 'Temperatura' },
  timestamp: { name: 'Fecha' },
  dateobserved: { name: 'Fecha de la medida' },
  startdate: { name: 'Inicio del intervalo' },
  enddate: { name: 'Fin del intervalo' },

  // Zona fusionada LIDAR + Smart Spot (predictions, etl/crowd)
  occupancy: { name: 'Ocupación' },
  confidence: {
    name: 'Origen de la cifra',
    description: 'Cómo se ha obtenido la ocupación: medida por un LIDAR o estimada a partir de los sensores WiFi/BLE.',
  },
  case: {
    name: 'Sensores de la zona',
    description: 'Qué sensores tiene la zona: LIDAR y WiFi/BLE, solo LIDAR o solo WiFi/BLE.',
  },
  smartspotsignal: {
    name: 'Señal de los sensores WiFi/BLE',
    description: 'Suma de lo que cuentan los sensores WiFi/BLE de la zona, sin calibrar. Sirve para diagnóstico.',
  },
  smartspotdeltapct: {
    name: 'Desviación de los sensores WiFi/BLE',
    description:
      'Diferencia, en %, entre lo que cuentan los sensores WiFi/BLE y el LIDAR. Positiva si los WiFi/BLE cuentan de más.',
  },
  lidarserial: { name: 'LIDAR de la zona', description: 'Identificadores de los LIDAR que cubren la zona.' },
  smartspotserial: {
    name: 'Sensores WiFi/BLE de la zona',
    description: 'Identificadores de los sensores WiFi/BLE que cubren la zona.',
  },
  // Sin productor en el repositorio: el significado de estas dos lo ha confirmado el equipo.
  occupancyratio: {
    name: 'Porcentaje de ocupación',
    description: 'Ocupación de la zona respecto a su aforo total.',
  },
  peoplecountinzone: {
    name: 'Recuento de la zona',
    description: 'Recuento conjunto de todos los dispositivos de la zona.',
  },
  // Sin productor en el repositorio: solo el nombre.
  capacity: { name: 'Aforo' },
  maxcapacity: { name: 'Aforo máximo' },
  peopledensity: { name: 'Densidad de personas' },
  peopleentering: { name: 'Personas que entran' },
  peopleleaving: { name: 'Personas que salen' },
  averagedwelltime: { name: 'Permanencia media' },
  casetype: { name: 'Tipo de caso' },
  // En pre toma los mismos valores que `confidence` de la fusion (measured, estimated), tambien en la prevision.
  confidencelevel: {
    name: 'Fiabilidad',
    description: 'Si la cifra se ha medido directamente o se ha estimado.',
  },
  lidarid: { name: 'LIDAR' },

  // Salud del LIDAR (predictions, etl/ote)
  framerate: { name: 'Imágenes por segundo', description: 'Imágenes recibidas del LIDAR por segundo en la hora.' },
  emptyframeratio: {
    name: 'Imágenes vacías',
    description: 'Proporción de imágenes sin ninguna detección, de 0 a 1.',
  },
  silencemaxseconds: {
    name: 'Mayor silencio',
    description: 'Tiempo más largo sin recibir imágenes del LIDAR en la hora, en segundos.',
  },
  lastframeat: { name: 'Última imagen recibida' },
  uptimehours: { name: 'Horas en funcionamiento' },
  transitions: {
    name: 'Pasos entre LIDAR (detalle)',
    description: 'Cuántos objetos han pasado de cada LIDAR de la zona a cada uno de los otros.',
  },

  // Prevision (predictions, etl/predict)
  predictedoccupancy: {
    name: 'Ocupación prevista',
    description: 'Personas que se espera que haya a la vez en la zona en esa hora, en un día sin eventos.',
  },
  predictedoccupancylower: {
    name: 'Ocupación prevista (mínimo)',
    description: 'Límite inferior del margen de la previsión, según los errores del modelo con esa antelación.',
  },
  predictedoccupancyupper: {
    name: 'Ocupación prevista (máximo)',
    description: 'Límite superior del margen de la previsión, según los errores del modelo con esa antelación.',
  },
  horizonstep: {
    name: 'Horas de antelación',
    description: 'Horas entre el último dato real y la hora prevista. Cuanto mayor, menos fiable.',
  },
  registeredevents: {
    name: 'Eventos registrados',
    description: 'Eventos registrados en la zona dentro del periodo de la previsión.',
  },
  zoneid: { name: 'Zona' },
  generatedat: { name: 'Fecha de la previsión', description: 'Cuándo se calculó la previsión.' },
  // Las publica en pre un productor distinto del de este repositorio. En sus datos,
  // predictedPeopleCount vale lo mismo que predictedOccupancy y los limites la rodean.
  predictedpeoplecount: {
    name: 'Personas previstas',
    description: 'Personas que se espera que haya a la vez en la zona en esa hora.',
  },
  confidencelower: {
    name: 'Límite inferior de la previsión',
    description: 'Límite inferior del intervalo de confianza de la previsión.',
  },
  confidenceupper: {
    name: 'Límite superior de la previsión',
    description: 'Límite superior del intervalo de confianza de la previsión.',
  },

  // Conteos de los sensores WiFi/BLE (CrowdFlowObserved)
  peoplecountshortinterval: {
    name: 'Dispositivos detectados (intervalo corto)',
    description: SMARTSPOT_COUNT('corto, de 1 a 3 minutos'),
  },
  peoplecountmediuminterval: {
    name: 'Dispositivos detectados (intervalo medio)',
    description: SMARTSPOT_COUNT('medio, de 2 a 5 minutos'),
  },
  peoplecountlonginterval: {
    name: 'Dispositivos detectados (intervalo largo)',
    description: SMARTSPOT_COUNT('largo, de 3 a 10 minutos'),
  },
  r_ts: { name: 'Hora del sensor', description: 'Hora que marca el propio sensor, en segundos desde 1970 (UTC).' },
  peoplecount: { name: 'Recuento de personas' },
  peoplecounttourist: { name: 'Recuento de turistas' },
  peoplecountresident: { name: 'Recuento de residentes' },
  peoplecountvisitor: { name: 'Recuento de visitantes' },

  // Detecciones de los sensores WiFi/BLE (CrowdFlowEvent)
  rssi: {
    name: 'Intensidad de la señal',
    description: 'Potencia con la que llegó la señal del dispositivo, en dBm. Cuanto más baja, más lejos estaba.',
  },
  random: {
    name: 'MAC aleatoria',
    description: 'Si el dispositivo usa una dirección MAC aleatoria, que cambia cada cierto tiempo.',
  },
  visitorid: { name: 'Identificador del visitante', description: 'Identificador seudónimo del dispositivo detectado.' },
  detectiontype: { name: 'Tipo de detección' },

  // ETL de afluencia (CrowdFlowEventETL)
  origin: { name: 'Origen', description: 'Sensor en el que empieza el recorrido.' },
  destination: { name: 'Destino', description: 'Sensor en el que acaba el recorrido.' },
  count: { name: 'Recuento' },
  visits: {
    name: 'Visitas',
    description:
      'Visitas al sensor. Una visita son detecciones seguidas en el mismo sensor y termina cuando la persona aparece en otro.',
  },
  uniquevisitors: { name: 'Visitantes únicos', description: 'Dispositivos distintos detectados en el sensor.' },
  newuniquevisitors: {
    name: 'Visitantes únicos nuevos',
    description:
      'Residentes y turistas clasificados por primera vez en el periodo. No incluye a los de corta estancia y es el mismo número en todos los sensores.',
  },
  newresidentuniquevisitors: {
    name: 'Residentes nuevos',
    description: 'Residentes clasificados o reclasificados en el periodo, incluidos los turistas que pasan a residentes.',
  },
  newtouristuniquevisitors: { name: 'Turistas nuevos', description: 'Turistas clasificados o reclasificados en el periodo.' },
  averagevisitduration: { name: 'Duración media de la visita', description: VISIT },
  minimumvisitduration: { name: 'Duración mínima de la visita', description: VISIT },
  maximumvisitduration: { name: 'Duración máxima de la visita', description: VISIT },
  averagetransitduration: { name: 'Duración media del recorrido', description: TRANSIT },
  minimumtransitduration: { name: 'Duración mínima del recorrido', description: TRANSIT },
  maximumtransitduration: { name: 'Duración máxima del recorrido', description: TRANSIT },
}

/** Metricas por hora del LIDAR (predictions, etl/ote), siempre detras de `total`, `adult` o `vehicle`. */
const LIDAR_METRICS: Record<string, MeasureInfo> = {
  count: { name: 'Objetos detectados', description: 'Objetos distintos que el LIDAR ha seguido en la hora.' },
  concurrentmax: {
    name: 'Máximo a la vez',
    description: 'Mayor número de objetos presentes a la vez en la hora.',
  },
  concurrentavg: {
    name: 'Media a la vez',
    description: 'Objetos presentes a la vez de media en la hora, ponderados por el tiempo.',
  },
  entered: { name: 'Entradas', description: 'Objetos que han aparecido dentro de la hora.' },
  exited: { name: 'Salidas', description: 'Objetos que se han ido dentro de la hora.' },
  stayavg: { name: 'Permanencia media', description: STAY },
  stayp50: { name: 'Permanencia mediana', description: STAY },
  stayp90: { name: 'Permanencia (percentil 90)', description: STAY },
  staymax: { name: 'Permanencia máxima', description: STAY },
  speedavg: { name: 'Velocidad media', description: 'En metros por segundo.' },
  speedp90: { name: 'Velocidad (percentil 90)', description: 'En metros por segundo.' },
  pathlengthavg: { name: 'Recorrido medio', description: 'Distancia media que recorre cada objeto, en metros.' },
  displacementavg: {
    name: 'Desplazamiento medio',
    description: 'Distancia media en línea recta entre donde aparece y donde se va cada objeto, en metros.',
  },
  stationarycount: { name: 'Objetos casi parados', description: 'Objetos que se han desplazado menos de 1 metro.' },
  transitions: { name: 'Pasos entre LIDAR', description: 'Veces que un objeto ha pasado de un LIDAR de la zona a otro.' },
}

const LIDAR_PREFIXES: Array<[prefix: string, label: string | null]> = [
  ['total', null],
  ['adult', 'adultos'],
  ['vehicle', 'vehículos'],
]

/** Campos en bruto del Smart Spot: llegan sin traducir al datamodel (ver smsp_fiware-datamodel.csv). */
const RAW_ALIASES: Record<string, string> = {
  r_cfo_counts: 'peoplecountshortinterval',
  r_cfo_countm: 'peoplecountmediuminterval',
  r_cfo_countl: 'peoplecountlonginterval',
  r_cfo_ts: 'r_ts',
  r_cfe_ts: 'r_ts',
  r_cfe_detecttype: 'detectiontype',
  r_cfe_random: 'random',
  r_cfe_rssi: 'rssi',
  r_cfe_visitorid: 'visitorid',
}

/** Grupos que las ETL anteponen a una metrica (`touristvisits`), con como se clasifica cada uno. */
const GROUPS: Array<[prefix: string, label: string, definition: string]> = [
  ['shorttermvisitor', 'corta estancia', 'Corta estancia: quien no es ni residente ni turista.'],
  [
    'resident',
    'residentes',
    'Residentes: vistos más de 2 días distintos, o que ya se habían clasificado antes y vuelven.',
  ],
  ['tourist', 'turistas', 'Turistas: vistos 1 o 2 días y más de 3 horas en total.'],
]

/** Ventanas que se posponen a una metrica: `uniqueVisitorsDaily`… */
const PERIODS: Array<[suffix: string, label: string]> = [
  ['biweekly', 'quincenal'],
  ['weekly', 'semanal'],
  ['monthly', 'mensual'],
  ['daily', 'diario'],
]

const lookup = (key: string): MeasureInfo | undefined => MEASURES[RAW_ALIASES[key] ?? key]

function qualify(base: MeasureInfo, qualifiers: Array<string | null>, definition?: string): MeasureInfo {
  const shown = qualifiers.filter((q): q is string => !!q)
  const name = shown.length ? `${base.name} (${shown.join(', ')})` : base.name
  const description = [base.description, definition].filter(Boolean).join(' ') || undefined
  return { name, description }
}

/** Separa el grupo, al principio o justo despues de `new` (`newTouristUniqueVisitors`). */
function splitGroup(key: string): [rest: string, label: string, definition: string] | null {
  for (const [prefix, label, definition] of GROUPS) {
    if (key.startsWith(prefix) && key.length > prefix.length) return [key.slice(prefix.length), label, definition]
    if (key.startsWith(`new${prefix}`)) return [`new${key.slice(prefix.length + 3)}`, label, definition]
  }
  return null
}

function lidarMetric(key: string): MeasureInfo | null {
  for (const [prefix, label] of LIDAR_PREFIXES) {
    const metric = key.startsWith(prefix) ? LIDAR_METRICS[key.slice(prefix.length)] : undefined
    if (metric) return qualify(metric, [label])
  }
  return null
}

export function measureInfo(id: string): MeasureInfo | null {
  const key = id.trim().toLowerCase()
  if (!key) return null

  const known = lookup(key) ?? lidarMetric(key)
  if (known) return known

  let rest = key
  let period: string | null = null
  const periodMatch = PERIODS.find(([suffix]) => rest.endsWith(suffix) && rest.length > suffix.length)
  if (periodMatch) {
    rest = rest.slice(0, -periodMatch[0].length)
    period = periodMatch[1]
  }

  const whole = lookup(rest)
  if (whole) return period ? qualify(whole, [period]) : null

  const group = splitGroup(rest)
  const base = group ? lookup(group[0]) : undefined
  if (!group || !base) return null
  return qualify(base, [group[1], period], group[2])
}

const SOURCE_VALUES = { measured: 'Medida', estimated: 'Estimada', estimated_uncalibrated: 'Estimada sin calibrar' }

/**
 * Valores de texto con significado fijo. Los de `case` y `confidence` estan comprobados en el
 * codigo que los publica (lidar_estimation.py); los demas son los que aparecen en pre.
 */
const VALUES: Record<string, Record<string, string>> = {
  confidencelevel: SOURCE_VALUES,
  casetype: { ...SOURCE_VALUES, mixed: 'Mixta' },
  case: { mixed: 'LIDAR y WiFi/BLE', lidar_only: 'Solo LIDAR', smartspot_only: 'Solo WiFi/BLE' },
  confidence: {
    measured: 'Medida por LIDAR',
    estimated: 'Estimada con WiFi/BLE',
    estimated_uncalibrated: 'Estimada con WiFi/BLE, sin calibrar',
    unknown: 'Sin datos',
  },
}

/** Texto de un valor conocido, o null para mostrarlo tal cual. */
export function measureValueLabel(id: string, value: unknown): string | null {
  const values = VALUES[id.trim().toLowerCase()]
  return (values && typeof value === 'string' && values[value.trim().toLowerCase()]) || null
}

/** Nombre traducido, o el que se tenga si la medida no esta en el catalogo. */
export function measureName(id: string, fallback?: string): string {
  return measureInfo(id)?.name ?? fallback ?? id
}

/** Traduce nombre y descripcion. El original queda en `sourceName` para las heuristicas en ingles. */
export function localizeMeasure<T extends { id: string; name: string }>(
  measure: T,
): T & { sourceName: string; description?: string } {
  const info = measureInfo(measure.id)
  if (!info) return { ...measure, sourceName: measure.name }
  return { ...measure, name: info.name, sourceName: measure.name, description: info.description }
}
