/**
 * Nombre, descripcion y, si hay un calculo detras, como se calcula cada medida de la plataforma.
 *
 * El servidor da el nombre en ingles de los CSV de datamodels o, si la variable no esta en
 * ninguno (todas las de afluencia), el identificador con el camelCase separado. Lo que no esta
 * aqui conserva ese nombre. Las claves van en minusculas: las ETL de afluencia no son
 * consistentes (`touristaverageVisitDuration` y `shortTermVisitorAverageVisitDuration`).
 *
 * Los calculos estan comprobados en el codigo que publica cada dato (predictions y las ETL de
 * afluencia del queues-consumer). Las variables sin productor en el repositorio, que en pre vienen
 * de datos de demostracion, solo se describen por lo que dice su nombre y no llevan calculo.
 */

export interface MeasureInfo {
  name: string
  /** Que es. Siempre existe: es lo que explica el icono de informacion del nombre. */
  description: string
  /** Como se obtiene, si no es una lectura directa. */
  calculation?: string
}

// Los textos los leen personas no tecnicas: lenguaje llano, sin siglas ni nombres de algoritmos.
const SECONDS = 'en segundos'
const VISIT = {
  description: 'Cuánto tiempo se queda la gente junto a un mismo sensor, ' + SECONDS + '.',
  calculation:
    'Se mide desde que el sensor detecta un dispositivo hasta la última vez que lo detecta seguido. La visita acaba cuando ese dispositivo aparece en otro sensor.',
}
const TRANSIT = {
  description: 'Cuánto se tarda en ir de un sensor a otro, ' + SECONDS + '.',
  calculation:
    'Se mide desde la última vez que un dispositivo se ve en el sensor de salida hasta la primera vez que se ve en el de llegada. Solo cuenta a quien pasa por los dos en la misma hora.',
}
const STAY_CALC =
  'Se mide desde que cada persona u objeto aparece hasta que se va. Solo cuenta a los que ya se han ido, para no dar tiempos a medias.'
const PHONES = (window: string) => ({
  description: `Dispositivos WiFi o Bluetooth que el sensor ha detectado en ${window}. Son dispositivos, no personas, y no indica cuántos había a la vez.`,
  calculation:
    'Se cuentan los dispositivos distintos que detecta el sensor en ese tiempo. El sensor da tres cifras a la vez, para un periodo corto, uno medio y uno largo.',
})

const MEASURES: Record<string, MeasureInfo> = {
  // Comunes
  name: { name: 'Nombre', description: 'Nombre con el que se muestra en la plataforma.' },
  location: { name: 'Ubicación', description: 'Dónde está, en el mapa.' },
  latitude: { name: 'Latitud', description: 'Posición en el mapa en sentido norte-sur.' },
  longitude: { name: 'Longitud', description: 'Posición en el mapa en sentido este-oeste.' },
  temperature: { name: 'Temperatura', description: 'Temperatura que mide el sensor.' },
  timestamp: { name: 'Fecha', description: 'Día y hora a los que corresponde el dato.' },
  dateobserved: { name: 'Fecha de la medida', description: 'Día y hora en que se tomó la medida.' },
  startdate: { name: 'Inicio del intervalo', description: 'Desde cuándo cuentan los datos.' },
  enddate: { name: 'Fin del intervalo', description: 'Hasta cuándo cuentan los datos.' },

  // Zona combinada LIDAR + sensores WiFi/BLE (predictions, etl/crowd)
  occupancy: {
    name: 'Ocupación',
    description:
      'Cuántas personas hay en la zona al mismo tiempo. No es cuántas han pasado por ella. Es la cifra principal de la zona.',
    calculation:
      'Si la zona tiene LIDAR y ha dado datos en esa hora, se usa lo que cuenta el LIDAR. Si no, se usa lo que detectan los sensores WiFi/BLE, ajustado con lo aprendido en las zonas que tienen los dos. Nunca se suman las dos cifras.',
  },
  confidence: {
    name: 'Origen de la cifra',
    description: 'Si la ocupación la ha contado un LIDAR o se ha estimado con los sensores WiFi/BLE.',
  },
  case: {
    name: 'Sensores de la zona',
    description: 'Qué sensores tiene la zona: LIDAR y WiFi/BLE, solo LIDAR o solo WiFi/BLE. De eso depende cómo se calcula la ocupación.',
  },
  smartspotsignal: {
    name: 'Señal de los sensores WiFi/BLE',
    description: 'Lo que detectan los sensores WiFi/BLE de la zona, tal cual. Sirve para revisar los sensores; no es la ocupación.',
    calculation: 'Se suman los dispositivos que detectan todos los sensores WiFi/BLE de la zona en esa hora.',
  },
  smartspotdeltapct: {
    name: 'Diferencia de los sensores WiFi/BLE',
    description: 'Cuánto se alejan los sensores WiFi/BLE de lo que cuenta el LIDAR en la misma zona. Si es positiva, cuentan de más.',
    calculation: 'Se compara lo que detectan con lo que cuenta el LIDAR y se da la diferencia en porcentaje. Solo en zonas con los dos sensores.',
  },
  lidarserial: { name: 'LIDAR de la zona', description: 'Qué LIDAR cubren la zona.' },
  smartspotserial: { name: 'Sensores WiFi/BLE de la zona', description: 'Qué sensores WiFi/BLE cubren la zona.' },
  // Sin productor en el repositorio: el significado de estas dos lo ha confirmado el equipo.
  occupancyratio: {
    name: 'Porcentaje de ocupación',
    description: 'Qué parte del aforo de la zona está ocupada.',
    calculation: 'Se divide la ocupación entre el aforo total de la zona.',
  },
  peoplecountinzone: {
    name: 'Recuento de la zona',
    description: 'Lo que cuentan entre todos los sensores de la zona. No es la ocupación que calcula la plataforma.',
    calculation: 'Se suma lo que cuenta cada sensor de la zona.',
  },
  // Sin productor en el repositorio: solo lo que dice su nombre.
  capacity: { name: 'Aforo', description: 'Cuántas personas caben en la zona.' },
  maxcapacity: { name: 'Aforo máximo', description: 'Número máximo de personas que admite la zona.' },
  peopledensity: { name: 'Densidad de personas', description: 'Cuántas personas hay por cada trozo de superficie de la zona.' },
  peopleentering: { name: 'Personas que entran', description: 'Personas que han entrado en la zona en ese tiempo.' },
  peopleleaving: { name: 'Personas que salen', description: 'Personas que han salido de la zona en ese tiempo.' },
  averagedwelltime: { name: 'Permanencia media', description: 'Tiempo que pasan de media las personas en la zona.' },
  casetype: { name: 'Tipo de caso', description: 'De qué forma se ha obtenido la cifra de la zona.' },
  // En pre toma los mismos valores que `confidence` de la fusion (measured, estimated), tambien en la prevision.
  confidencelevel: { name: 'Fiabilidad', description: 'Si la cifra se ha contado directamente o se ha estimado.' },
  lidarid: { name: 'LIDAR', description: 'Qué LIDAR cubre la zona.' },

  // Estado de los LIDAR (predictions, etl/ote)
  framerate: {
    name: 'Imágenes por segundo',
    description: 'Cuántas imágenes envía el LIDAR cada segundo. Si baja, el sensor va lento o pierde la conexión.',
    calculation: 'Se dividen las imágenes recibidas en la hora entre los segundos de la hora.',
  },
  emptyframeratio: {
    name: 'Imágenes vacías',
    description: 'Qué parte de las imágenes del LIDAR no tenía a nadie. 0 es ninguna y 1 es todas.',
    calculation: 'Se dividen las imágenes en las que no se detecta a nadie entre todas las recibidas en la hora.',
  },
  silencemaxseconds: {
    name: 'Mayor silencio',
    description: 'El rato más largo de la hora en que no llegó nada del LIDAR, ' + SECONDS + '.',
  },
  lastframeat: { name: 'Última imagen recibida', description: 'Cuándo llegó la última imagen del LIDAR.' },
  uptimehours: { name: 'Horas en funcionamiento', description: 'Cuántas horas lleva funcionando el LIDAR.' },
  transitions: {
    name: 'Pasos entre LIDAR (detalle)',
    description: 'Cuántas personas u objetos han pasado de cada LIDAR de la zona a cada uno de los otros en la hora.',
  },

  // Prevision (predictions, etl/predict)
  predictedoccupancy: {
    name: 'Ocupación prevista',
    description: 'Cuántas personas se espera que haya a la vez en la zona a esa hora, en un día normal, sin eventos.',
    calculation:
      'La calcula un modelo que aprende del histórico de la zona: lo que suele haber según la hora, el día de la semana, los festivos y el tiempo. No aprende de los días con eventos registrados; los eventos se suman después en el simulador.',
  },
  predictedoccupancylower: {
    name: 'Ocupación prevista (mínimo)',
    description: 'Lo mínimo que se espera, para tener en cuenta que la previsión puede fallar.',
    calculation: 'Se calcula con lo que se equivocó la previsión en el pasado: solo 1 de cada 10 veces la cifra real quedó por debajo.',
  },
  predictedoccupancyupper: {
    name: 'Ocupación prevista (máximo)',
    description: 'Lo máximo que se espera, para tener en cuenta que la previsión puede fallar.',
    calculation: 'Se calcula con lo que se equivocó la previsión en el pasado: solo 1 de cada 10 veces la cifra real quedó por encima.',
  },
  horizonstep: {
    name: 'Horas de antelación',
    description: 'Con cuántas horas de antelación se ha hecho la previsión. Cuantas más, menos fiable.',
    calculation: 'Cada hora se prevé a partir de las anteriores, así que el margen de error crece con la antelación.',
  },
  registeredevents: {
    name: 'Eventos registrados',
    description: 'Eventos apuntados en la zona para esos días. La previsión no los incluye: se suman en el simulador.',
  },
  zoneid: { name: 'Zona', description: 'Zona a la que corresponde la previsión.' },
  generatedat: { name: 'Fecha de la previsión', description: 'Cuándo se hizo la previsión.' },
  // Las publica en pre un productor distinto del de este repositorio. En sus datos,
  // predictedPeopleCount vale lo mismo que predictedOccupancy y los limites la rodean.
  predictedpeoplecount: {
    name: 'Personas previstas',
    description: 'Cuántas personas se espera que haya a la vez en la zona a esa hora. Es lo mismo que la ocupación prevista.',
  },
  confidencelower: { name: 'Límite inferior de la previsión', description: 'Lo mínimo que se espera, por si la previsión falla.' },
  confidenceupper: { name: 'Límite superior de la previsión', description: 'Lo máximo que se espera, por si la previsión falla.' },

  // Conteos de los sensores WiFi/BLE (CrowdFlowObserved)
  peoplecountshortinterval: { name: 'Dispositivos detectados (periodo corto)', ...PHONES('el periodo corto, de 1 a 3 minutos') },
  peoplecountmediuminterval: { name: 'Dispositivos detectados (periodo medio)', ...PHONES('el periodo medio, de 2 a 5 minutos') },
  peoplecountlonginterval: { name: 'Dispositivos detectados (periodo largo)', ...PHONES('el periodo largo, de 3 a 10 minutos') },
  r_ts: { name: 'Hora del sensor', description: 'Hora que marcaba el propio sensor al tomar la medida, en segundos desde 1970 (UTC).' },
  peoplecount: { name: 'Recuento de personas', description: 'Personas que ha contado el sensor en ese tiempo.' },
  peoplecounttourist: { name: 'Recuento de turistas', description: 'Parte del recuento que son turistas.' },
  peoplecountresident: { name: 'Recuento de residentes', description: 'Parte del recuento que son residentes.' },
  peoplecountvisitor: { name: 'Recuento de visitantes', description: 'Parte del recuento que son visitantes.' },

  // Detecciones de los sensores WiFi/BLE (CrowdFlowEvent)
  rssi: {
    name: 'Intensidad de la señal',
    description: 'Con cuánta fuerza llegó la señal del dispositivo, en dBm. Cuanto más baja, más lejos estaba.',
  },
  random: {
    name: 'MAC aleatoria',
    description: 'Si el dispositivo usa una dirección MAC aleatoria, que cambia cada cierto tiempo para proteger su privacidad.',
  },
  visitorid: {
    name: 'Identificador del visitante',
    description: 'Código que identifica al dispositivo detectado sin saber de quién es. Permite seguirlo de un sensor a otro.',
  },
  detectiontype: { name: 'Tipo de detección', description: 'Si el dispositivo se detectó por WiFi o por BLE (Bluetooth).' },

  // Visitas y recorridos (CrowdFlowEventETL)
  origin: { name: 'Origen', description: 'Sensor donde empieza el recorrido.' },
  destination: { name: 'Destino', description: 'Sensor donde acaba el recorrido.' },
  count: {
    name: 'Recuento',
    description:
      'En un recorrido: cuántas veces se ha ido del sensor de salida al de llegada en esa hora. Una misma persona puede contar más de una vez.',
    calculation:
      'Se cuentan los dispositivos que se ven primero en un sensor y después en el otro dentro de la misma hora. Si salida y llegada son el mismo sensor, junta todos los recorridos que entran o salen de él.',
  },
  visits: {
    name: 'Visitas',
    description: 'Cuántas veces se ha pasado por el sensor en esa hora. Una misma persona puede sumar varias visitas.',
    calculation: 'Una visita es el rato seguido en que un dispositivo está junto al sensor; acaba cuando ese dispositivo aparece en otro sensor.',
  },
  uniquevisitors: {
    name: 'Visitantes únicos',
    description: 'Cuántas personas distintas ha detectado el sensor. Cada una cuenta una vez, aunque haga varias visitas.',
    calculation: 'Se cuentan los dispositivos distintos detectados en ese tiempo: la hora, si no se dice otro periodo.',
  },
  newuniquevisitors: {
    name: 'Visitantes únicos nuevos',
    description: 'Residentes y turistas que aparecen por primera vez en ese tiempo. Es la misma cifra en todos los sensores.',
    calculation: 'Se cuentan los que se clasifican por primera vez como residentes o turistas. No incluye a los de corta estancia.',
  },
  newresidentuniquevisitors: {
    name: 'Residentes nuevos',
    description: 'Personas que han pasado a considerarse residentes en ese tiempo.',
    calculation: 'Incluye a los turistas que vuelven y pasan a ser residentes. La clasificación se rehace cada semana.',
  },
  newtouristuniquevisitors: {
    name: 'Turistas nuevos',
    description: 'Personas que han pasado a considerarse turistas en ese tiempo.',
    calculation: 'La clasificación se rehace cada semana.',
  },
  averagevisitduration: { name: 'Duración media de la visita', ...VISIT },
  minimumvisitduration: { name: 'Duración mínima de la visita', ...VISIT },
  maximumvisitduration: { name: 'Duración máxima de la visita', ...VISIT },
  averagetransitduration: { name: 'Duración media del recorrido', ...TRANSIT },
  minimumtransitduration: { name: 'Duración mínima del recorrido', ...TRANSIT },
  maximumtransitduration: { name: 'Duración máxima del recorrido', ...TRANSIT },
}

/** Metricas por hora del LIDAR (predictions, etl/ote), siempre detras de `total`, `adult` o `vehicle`. */
const LIDAR_METRICS: Record<string, MeasureInfo> = {
  count: {
    name: 'Detectados en la hora',
    description: 'Cuántas personas u objetos distintos ha visto el LIDAR en la hora: cuántos han pasado, no cuántos había a la vez.',
  },
  concurrentmax: {
    name: 'Máximo a la vez',
    description: 'El mayor número de personas u objetos que el LIDAR ha visto a la vez en la hora.',
    calculation: 'Es la cifra que se usa para calcular la ocupación de la zona.',
  },
  concurrentavg: {
    name: 'Media a la vez',
    description: 'Cuántas personas u objetos había a la vez, de media, durante la hora.',
    calculation: 'Cuenta más lo que dura más: diez personas durante media hora pesan más que diez durante un minuto.',
  },
  entered: { name: 'Entradas', description: 'Cuántos han aparecido en la hora.' },
  exited: { name: 'Salidas', description: 'Cuántos se han ido en la hora.' },
  stayavg: { name: 'Permanencia media', description: 'Tiempo que se queda cada uno de media a la vista del LIDAR, ' + SECONDS + '.', calculation: STAY_CALC },
  stayp50: {
    name: 'Permanencia típica',
    description: 'La mitad de los detectados se queda menos que esto a la vista del LIDAR, y la otra mitad, más; ' + SECONDS + '.',
    calculation: STAY_CALC,
  },
  stayp90: {
    name: 'Permanencia larga',
    description: 'Solo 1 de cada 10 detectados se queda más que esto a la vista del LIDAR; ' + SECONDS + '.',
    calculation: STAY_CALC,
  },
  staymax: { name: 'Permanencia máxima', description: 'El tiempo más largo a la vista del LIDAR, ' + SECONDS + '.', calculation: STAY_CALC },
  speedavg: { name: 'Velocidad media', description: 'A qué velocidad se mueven de media, en metros por segundo.' },
  speedp90: {
    name: 'Velocidad alta',
    description: 'Solo 1 de cada 10 detectados va más rápido que esto; en metros por segundo.',
  },
  pathlengthavg: {
    name: 'Recorrido medio',
    description: 'Cuántos metros recorre cada uno de media, contando todas sus vueltas.',
  },
  displacementavg: {
    name: 'Desplazamiento medio',
    description: 'Distancia media en línea recta entre donde aparece cada uno y donde se va, en metros.',
  },
  stationarycount: {
    name: 'Casi parados',
    description: 'Cuántos apenas se han movido mientras estaban a la vista.',
    calculation: 'Se cuentan los que se han desplazado menos de 1 metro entre que aparecen y se van.',
  },
  transitions: {
    name: 'Pasos entre LIDAR',
    description: 'Cuántas veces alguien ha pasado de un LIDAR de la zona a otro en la hora.',
  },
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
  ['shorttermvisitor', 'corta estancia', 'Corta estancia: quien no llega a ser residente ni turista.'],
  ['resident', 'residentes', 'Residentes: los que se ven más de 2 días distintos, o los que ya se habían visto antes y vuelven.'],
  ['tourist', 'turistas', 'Turistas: los que se ven 1 o 2 días y pasan más de 3 horas en total.'],
]

/** Ventanas que se posponen a una metrica (`uniqueVisitorsDaily`), contadas hacia atras desde el calculo. */
const PERIODS: Array<[suffix: string, label: string, window: string]> = [
  ['biweekly', 'quincenal', 'Cuenta las dos semanas anteriores.'],
  ['weekly', 'semanal', 'Cuenta la semana anterior.'],
  ['monthly', 'mensual', 'Cuenta el mes anterior.'],
  ['daily', 'diario', 'Cuenta el día anterior.'],
]

const lookup = (key: string): MeasureInfo | undefined => MEASURES[RAW_ALIASES[key] ?? key]

function qualify(
  base: MeasureInfo,
  qualifiers: Array<string | null>,
  definition?: string,
  window?: string,
): MeasureInfo {
  const shown = qualifiers.filter((q): q is string => !!q)
  const name = shown.length ? `${base.name} (${shown.join(', ')})` : base.name
  const description = [base.description, definition].filter(Boolean).join(' ')
  const calculation = [base.calculation, window].filter(Boolean).join(' ') || undefined
  return { ...base, name, description, calculation }
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
  const periodMatch = PERIODS.find(([suffix]) => rest.endsWith(suffix) && rest.length > suffix.length)
  if (periodMatch) rest = rest.slice(0, -periodMatch[0].length)
  const [period, window] = periodMatch ? [periodMatch[1], periodMatch[2]] : [null, undefined]

  const whole = lookup(rest)
  if (whole) return period ? qualify(whole, [period], undefined, window) : null

  const group = splitGroup(rest)
  const base = group ? lookup(group[0]) : undefined
  if (!group || !base) return null
  return qualify(base, [group[1], period], group[2], window)
}

const SOURCE_VALUES = { measured: 'Contada', estimated: 'Estimada', estimated_uncalibrated: 'Estimada sin ajustar' }

/**
 * Valores de texto con significado fijo. Los de `case` y `confidence` estan comprobados en el
 * codigo que los publica (lidar_estimation.py); los demas son los que aparecen en pre.
 */
const VALUES: Record<string, Record<string, string>> = {
  confidencelevel: SOURCE_VALUES,
  casetype: { ...SOURCE_VALUES, mixed: 'Mixta' },
  case: { mixed: 'LIDAR y WiFi/BLE', lidar_only: 'Solo LIDAR', smartspot_only: 'Solo WiFi/BLE' },
  confidence: {
    measured: 'Contada por LIDAR',
    estimated: 'Estimada con WiFi/BLE',
    estimated_uncalibrated: 'Estimada con WiFi/BLE, sin ajustar',
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

/** Traduce nombre, descripcion y calculo. El original queda en `sourceName` para las heuristicas en ingles. */
export function localizeMeasure<T extends { id: string; name: string }>(
  measure: T,
): T & { sourceName: string; description?: string; calculation?: string } {
  const info = measureInfo(measure.id)
  if (!info) return { ...measure, sourceName: measure.name }
  return {
    ...measure,
    name: info.name,
    sourceName: measure.name,
    description: info.description,
    calculation: info.calculation,
  }
}
