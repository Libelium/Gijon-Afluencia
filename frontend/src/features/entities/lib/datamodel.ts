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
 * Nombre en castellano de los modelos de datos de afluencia. Se indexa por la clave del contrato
 * y no por el nombre: los nombres son contrato heredado y no se escriben como literales.
 */
const LABELS: Partial<Record<DatamodelKey, string>> = {
  zone: 'Zona de afluencia',
  zoneScan: 'Zona medida por LIDAR',
  zonePrediction: 'Previsión de afluencia',
  flowObserved: 'Conteos WiFi/BLE',
  rawEvent: 'Detecciones WiFi/BLE',
  flowEvent: 'Visitas y recorridos',
  peopleCount: 'Conteo de personas',
  lidarObserved: 'Conteos por LIDAR',
  lidarDevice: 'Estado de los LIDAR',
}

let byName: Map<string, string> | null = null

/** Nombre legible de un modelo de datos, o el propio nombre si no se conoce. */
export function datamodelLabel(datamodel?: string | null): string {
  const name = String(datamodel ?? '')
  byName ??= new Map(
    (Object.entries(LABELS) as [DatamodelKey, string][]).map(([key, label]) => [datamodelOf(key), label]),
  )
  return byName.get(name) ?? name
}
