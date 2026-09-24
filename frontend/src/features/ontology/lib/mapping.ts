/**
 * Correspondencia entre los elementos de la plataforma y la ontologia de turismo de SEGITTUR.
 *
 * El nucleo de SEGITTUR describe recursos turisticos (destino, plaza, iglesia, ruta...) y su aforo
 * (`capacity`), pero no define sensores ni observaciones. Por eso los PIT se tipan con clases de
 * SEGITTUR y las medidas siguen los Smart Data Models de FIWARE, enlazadas al PIT por su zona.
 * Los identificadores de zona son los del despliegue de Cimavilla y el Cerro de Santa Catalina.
 */

export interface PitMapping {
  zoneId: string
  name: string
  classId: string
}

export interface PropertyMapping {
  property: string
  source: string
}

export interface ElementMapping {
  element: string
  classId: string | null
  description: string
  properties?: PropertyMapping[]
}

export interface MeasurementMapping {
  datamodel: string
  description: string
  relation: string
}

export const DESTINATION: ElementMapping = {
  element: 'Gijón / Xixón',
  classId: 'TourismDestination',
  description:
    'El municipio es el destino turístico al que pertenecen todos los recursos que se monitorizan.',
  properties: [
    { property: 'name', source: 'Gijón / Xixón' },
    { property: 'destinationType', source: 'Destino de costa (tesauro «Tipo de destino»)' },
    { property: 'hasLocation', source: 'Localidad Gijón, provincia Asturias, Principado de Asturias' },
  ],
}

export const SITE: ElementMapping = {
  element: 'Cimavilla y Cerro de Santa Catalina',
  classId: 'TouristAttractionSite',
  description:
    'Conjunto histórico en el que se despliega la red de sensores y que agrupa los puntos de interés turístico.',
  properties: [{ property: 'relatedTourismDestination', source: 'Gijón / Xixón' }],
}

/** Propiedades con que cada PIT se describe en SEGITTUR y de donde sale su valor. */
export const PIT_PROPERTIES: PropertyMapping[] = [
  { property: 'name', source: 'Nombre visible de la zona' },
  { property: 'capacity', source: 'Aforo máximo configurado para la zona (personas simultáneas)' },
  { property: 'hasLocation', source: 'Ubicación de la zona (centroide de sus sensores)' },
  { property: 'relatedTourismDestination', source: 'Gijón / Xixón' },
]

export const PITS: PitMapping[] = [
  { zoneId: 'bateria_alta', name: 'Batería Alta', classId: 'HistoricalOrCulturalResource' },
  { zoneId: 'bateria_baja', name: 'Batería Baja', classId: 'HistoricalOrCulturalResource' },
  { zoneId: 'plaza_fermin_garcia', name: 'Plaza de Fermín García Bernardo', classId: 'Square' },
  { zoneId: 'cuesta_cholo', name: "Cuesta'l Cholo", classId: 'Square' },
  { zoneId: 'camin_fontica', name: 'Camín de la Fóntica', classId: 'Route' },
  { zoneId: 'plaza_tabacalera', name: 'Plaza de Tabacalera', classId: 'Square' },
  { zoneId: 'plaza_corrada', name: 'Plaza de la Corrada', classId: 'Square' },
  { zoneId: 'plaza_soledad', name: 'Plaza de la Soledad', classId: 'Square' },
  { zoneId: 'plazuela_jovellanos', name: 'Plazuela de Jovellanos', classId: 'Square' },
  { zoneId: 'plaza_colegiata', name: 'Plaza de la Colegiata', classId: 'Square' },
  { zoneId: 'iglesia_san_pedro', name: 'Iglesia de San Pedro', classId: 'Church' },
  { zoneId: 'campo_valdes', name: 'Campo Valdés', classId: 'Square' },
  { zoneId: 'oficina_turismo', name: 'Plaza de la Oficina de Turismo', classId: 'Square' },
  { zoneId: 'plaza_mayor', name: 'Plaza Mayor', classId: 'Square' },
]

/** Clases de SEGITTUR relacionadas que no tipan un PIT pero si aparecen en el despliegue. */
export const RELATED: ElementMapping[] = [
  {
    element: 'Oficina de turismo de Cimavilla',
    classId: 'TouristInformationOffice',
    description: 'Servicio público junto al PIT «Plaza de la Oficina de Turismo».',
  },
]

export const MEASUREMENTS: MeasurementMapping[] = [
  {
    datamodel: 'CrowdFlowZone',
    description: 'Aforo agregado de la zona: ocupación actual y afluencia acumulada.',
    relation: 'Es el PIT: misma zona, su aforo máximo es «capacity».',
  },
  {
    datamodel: 'CrowdFlowLidarZone',
    description: 'Ocupación de la zona medida por los LIDAR.',
    relation: 'Medida del PIT, enlazada por el identificador de zona.',
  },
  {
    datamodel: 'CrowdFlowObserved',
    description: 'Conteos agregados de personas de cada Smart Spot.',
    relation: 'Observación situada en un PIT, enlazada por su zona.',
  },
  {
    datamodel: 'CrowdFlowLidarDevice',
    description: 'Estado de cada sensor LIDAR.',
    relation: 'Sensor desplegado en un PIT. SEGITTUR no modela sensores.',
  },
  {
    datamodel: 'CrowdFlowPrediction',
    description: 'Proyección del aforo de la zona en las próximas horas.',
    relation: 'Predicción sobre el aforo («capacity») del PIT.',
  },
  {
    datamodel: 'CrowdFlowEvent',
    description: 'Tránsitos agregados entre zonas, sin datos personales.',
    relation: 'Flujo entre dos PIT, enlazado por las zonas de origen y destino.',
  },
]

/** Todas las clases de SEGITTUR que usa la correspondencia, para validarlas contra los datos. */
export function mappedClassIds(): string[] {
  const ids = [DESTINATION, SITE, ...RELATED].map((e) => e.classId)
  return [...new Set([...ids, ...PITS.map((p) => p.classId)].filter((id): id is string => !!id))]
}

/** Numero de PIT por clase, para la leyenda de la correspondencia. */
export function pitsByClass(): Map<string, number> {
  const counts = new Map<string, number>()
  for (const pit of PITS) counts.set(pit.classId, (counts.get(pit.classId) ?? 0) + 1)
  return counts
}
