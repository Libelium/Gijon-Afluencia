import { datamodelOf, type DatamodelKey } from '@/features/dashboards/templates/contract'

/**
 * Un icono por familia de modelo de datos. Orienta la lectura del listado mucho mas que el
 * nombre solo, que suele ser un termino tecnico en ingles. El orden importa: gana la primera
 * familia que coincide, asi que lo especifico va antes que lo generico.
 */
const ICONS: readonly (readonly [RegExp, string])[] = [
  [/waste|garbage|container|recycl/i, 'mdi-trash-can-outline'],
  [/water|hydro|irrigat|pool|flood|sewer/i, 'mdi-water-outline'],
  [/weather|meteo|temperature|humidity|climate|rain|wind/i, 'mdi-weather-partly-cloudy'],
  [/air.?quality|pollut|emission/i, 'mdi-air-filter'],
  [/noise|acoustic|sound|decibel/i, 'mdi-volume-high'],
  [/light|lamp|luminair/i, 'mdi-lightbulb-outline'],
  [/parking|vehicle|traffic|road|bicycl/i, 'mdi-car-outline'],
  [/tree|garden|park\b|forest|agri|parcel|crop|soil|green/i, 'mdi-tree-outline'],
  [/flowobserved|people|pedestrian|footfall|occupanc|aforo|visitor/i, 'mdi-account-group-outline'],
  [/card|payment|transaction|purchase|invoice/i, 'mdi-credit-card-outline'],
  [/energy|power|electric|phase|voltage|photovolt|solar|batter|charg|meter/i, 'mdi-flash-outline'],
  [/incident|alarm|alert|issue/i, 'mdi-alert-circle-outline'],
  [/intervention|maintenance|work.?order|repair/i, 'mdi-wrench-outline'],
  [/building|facilit|asset|infrastructure/i, 'mdi-office-building-outline'],
  [/device|sensor|probe|gateway/i, 'mdi-chip'],
]

export const DATAMODEL_ICON_FALLBACK = 'mdi-database-outline'

export function datamodelIcon(datamodel?: string | null): string {
  const name = String(datamodel ?? '')
  if (!name) return DATAMODEL_ICON_FALLBACK
  for (const [pattern, icon] of ICONS) {
    if (pattern.test(name)) return icon
  }
  return DATAMODEL_ICON_FALLBACK
}

/**
 * Nombre, descripcion y origen de los modelos de datos de afluencia. Se indexa por la clave del
 * contrato y no por el nombre: los nombres son contrato heredado y no se escriben como literales.
 * El origen esta comprobado en el codigo que publica cada uno (predictions y las ETL de afluencia).
 */
export interface DatamodelInfo {
  label: string
  description: string
  /** De donde salen sus datos y, si los calcula la plataforma, como. */
  source: string
}

// Lo leen personas no tecnicas: lenguaje llano, sin siglas ni identificadores internos.
const INFO: Partial<Record<DatamodelKey, DatamodelInfo>> = {
  zone: {
    label: 'Zona de afluencia (combinada)',
    description: 'La cifra final de cada zona: cuántas personas hay a la vez. Hay una por zona, tenga los sensores que tenga.',
    source:
      'La calcula la plataforma cada hora con los LIDAR y los sensores WiFi/BLE de la zona. Si hay LIDAR con datos, se usa el LIDAR; si no, los sensores WiFi/BLE. Qué sensores tiene la zona lo dice su dato «Sensores de la zona».',
  },
  zoneScan: {
    label: 'Zona de afluencia (solo LIDAR)',
    description:
      'Lo que ven los LIDAR de una zona, sin los sensores WiFi/BLE: personas a la vez, entradas y salidas, cuánto se quedan, a qué velocidad van…',
    source: 'La calcula la plataforma cada hora con lo que envían los LIDAR de la zona. Si dos LIDAR ven a la misma persona, cuenta una vez.',
  },
  zonePrediction: {
    label: 'Previsión de afluencia',
    description: 'Cuántas personas se espera que haya en una zona en las próximas horas, en un día normal, sin eventos.',
    source: 'La calcula cada día un modelo que aprende del histórico de la zona.',
  },
  flowObserved: {
    label: 'Conteos WiFi/BLE (por sensor)',
    description: 'Lo que cuenta un sensor WiFi/BLE: cuántos dispositivos detecta en periodos de unos minutos.',
    source: 'Los envía el propio sensor.',
  },
  rawEvent: {
    label: 'Detecciones WiFi/BLE (por sensor)',
    description: 'Cada dispositivo que detecta un sensor WiFi/BLE, con un código que lo identifica sin saber de quién es.',
    source: 'Los envía el propio sensor.',
  },
  flowEvent: {
    label: 'Visitas y recorridos',
    description:
      'Visitas a cada sensor WiFi/BLE, personas distintas, cuánto duran las visitas y los recorridos entre sensores, separando residentes, turistas y corta estancia.',
    source: 'Los calcula la plataforma cada hora a partir de lo que detectan los sensores WiFi/BLE.',
  },
  peopleCount: {
    label: 'Conteo de personas',
    description: 'Personas que cuenta un sensor de conteo.',
    source: 'Los envía el propio sensor.',
  },
  lidarObserved: {
    label: 'Conteos por LIDAR (por sensor)',
    description: 'Lo mismo que la zona solo LIDAR, pero de un único LIDAR: sirve para ver cuál de ellos recoge más gente.',
    source: 'La calcula la plataforma cada hora con lo que envía ese LIDAR.',
  },
  lidarDevice: {
    label: 'Estado de los LIDAR',
    description: 'Si cada LIDAR funciona bien: cuántas imágenes envía, cuántas llegan vacías y el rato más largo sin enviar nada.',
    source: 'La calcula la plataforma cada hora con lo que envía ese LIDAR.',
  },
}

let byName: Map<string, DatamodelInfo> | null = null

/** Nombre, descripcion y origen de un modelo de datos, o null si no se conoce. */
export function datamodelInfo(datamodel?: string | null): DatamodelInfo | null {
  byName ??= new Map(
    (Object.entries(INFO) as [DatamodelKey, DatamodelInfo][]).map(([key, info]) => [datamodelOf(key), info]),
  )
  return byName.get(String(datamodel ?? '')) ?? null
}

/** Nombre legible de un modelo de datos, o el propio nombre si no se conoce. */
export function datamodelLabel(datamodel?: string | null): string {
  return datamodelInfo(datamodel)?.label ?? String(datamodel ?? '')
}
