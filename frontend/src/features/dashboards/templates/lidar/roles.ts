/**
 * Los sensores publican el mismo dato con nombres distintos segun firmware, asi que los
 * papeles se resuelven por tabla de candidatos y no por un identificador fijo: una zona
 * nueva se soporta anadiendo un candidato aqui, sin tocar las vistas.
 */
export type RoleKey =
  | 'occupancy'
  | 'ratio'
  | 'capacity'
  | 'dwell'
  | 'density'
  | 'inflow'
  | 'outflow'
  | 'predicted'
  | 'predLower'
  | 'predUpper'
  | 'confidence'
  | 'case'
  | 'sensor'

export function normalizeId(raw: string): string {
  return raw.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export const HIDDEN_IDS: readonly string[] = [
  'location',
  'name',
  'id',
  'type',
  'urn',
  'tenant',
  'scope',
  'entityid',
  'template',
  'datamodel',
]

export const ROLE_CANDIDATES: Record<RoleKey, readonly string[]> = {
  occupancy: [
    'peoplecountinzone',
    'zoneoccupancy',
    'peopleinzone',
    'peoplecount',
    'personcount',
    'occupancynumber',
    'currentoccupancy',
    'occupancycount',
    'peoplecountlonginterval',
    'peoplecountshortinterval',
    'count',
  ],
  ratio: ['occupancyratio', 'occupancylevel', 'occupancypercentage', 'occupancypercent', 'loadfactor', 'occupancy'],
  capacity: [
    'maxcapacity',
    'maximumcapacity',
    'zonecapacity',
    'totalcapacity',
    'capacitymax',
    'maxoccupancy',
    'capacity',
  ],
  dwell: [
    'averagedwelltime',
    'avgdwelltime',
    'meandwelltime',
    'dwelltime',
    'stayduration',
    'residencetime',
    'permanencetime',
  ],
  density: ['peopledensity', 'occupancydensity', 'density'],
  inflow: ['peopleentering', 'entriescount', 'entrycount', 'inflow', 'entries', 'entradas'],
  outflow: ['peopleleaving', 'exitscount', 'exitcount', 'outflow', 'exits', 'salidas'],
  predicted: [
    'predictedpeoplecount',
    'predictedoccupancy',
    'predictedvalue',
    'forecastvalue',
    'predictionvalue',
    'prediction',
    'predicted',
    'forecast',
    'yhat',
    'value',
  ],
  predLower: ['confidencelower', 'predictedmin', 'lowerbound', 'minvalue', 'yhatlower', 'minimum', 'lower', 'min'],
  predUpper: ['confidenceupper', 'predictedmax', 'upperbound', 'maxvalue', 'yhatupper', 'maximum', 'upper', 'max'],
  confidence: ['confidencelevel', 'confidence', 'reliability', 'fiabilidad'],
  case: ['casetype', 'usecase', 'scenario', 'situation', 'case'],
  sensor: ['lidarid', 'sensorid', 'deviceid', 'refdevice', 'sensor', 'source'],
}

const rank = (a: string, b: string): number => a.length - b.length || a.localeCompare(b, 'es')

export function matchRole(ids: string[], role: RoleKey): string | null {
  const wanted = ROLE_CANDIDATES[role]

  for (const candidate of wanted) {
    const hits = ids.filter((id) => normalizeId(id) === candidate).sort(rank)
    if (hits.length) return hits[0]
  }

  // Contencion solo con candidatos de 5 caracteres o mas: 'min' casaria con 'minimum'
  // y 'case' con 'lowercase'.
  for (const candidate of wanted) {
    if (candidate.length < 5) continue
    const hits = ids.filter((id) => normalizeId(id).includes(candidate)).sort(rank)
    if (hits.length) return hits[0]
  }

  return null
}
