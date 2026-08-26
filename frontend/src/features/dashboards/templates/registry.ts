import type { Component } from 'vue'
import { defineAsyncComponent } from 'vue'
import type { DatamodelKey, TemplateKey } from './contract'
import { datamodelsOf, keyOfTypeId, typeIdOf } from './contract'

export type TemplateFamily = 'occupancy' | 'lidar'

export interface TemplateDescriptor {
  key: TemplateKey
  family: TemplateFamily
  /** Rotulo visible, descriptivo de la funcion. */
  label: string
  description: string
  icon: string
  /** Vista que dibuja la plantilla. Recibe la prop `dashboard`. */
  view: Component
  /** Modelos de datos que la plantilla sabe interpretar, para filtrar el selector. */
  datamodels: DatamodelKey[]
}

const lazy = (loader: () => Promise<unknown>) =>
  defineAsyncComponent(loader as () => Promise<{ default: Component }>)

/**
 * Registro explicito. Un mapa en lugar de una busqueda sobre todo lo exportado por una
 * carpeta: permite que el paquete final solo cargue la plantilla que se abre, y deja un unico
 * sitio donde anadir o quitar plantillas.
 *
 * Toda clave de `TemplateKey` tiene que figurar aqui, y su vista tiene que existir en disco: un
 * importe dinamico que no se resuelve tumba la construccion del paquete y con ella toda la
 * seccion de cuadros de mando. Si hay que anadir un identificador antes de escribir su vista,
 * cambiar el tipo a Partial<Record<...>> y dejarla fuera; `resolveTemplate` ya devuelve null y
 * `TemplateHost` muestra el aviso previsto.
 */
export const TEMPLATES: Record<TemplateKey, TemplateDescriptor> = {
  occupancy: {
    key: 'occupancy',
    family: 'occupancy',
    label: 'Aforo · Monitorización',
    description: 'Ocupación por punto de medida, con mapa, evolución temporal y reparto por franjas.',
    icon: 'mdi-account-group-outline',
    view: lazy(() => import('./occupancy/OccupancyTemplate.vue')),
    datamodels: ['flowObserved', 'peopleCount'],
  },
  classification: {
    key: 'classification',
    family: 'occupancy',
    label: 'Aforo · Clasificación',
    description: 'Reparto de personas por categoría detectada, con evolución y totales.',
    icon: 'mdi-account-multiple-outline',
    view: lazy(() => import('./classification/ClassificationTemplate.vue')),
    datamodels: ['flowObserved', 'peopleCount'],
  },
  classificationAdvanced: {
    key: 'classificationAdvanced',
    family: 'occupancy',
    label: 'Aforo · Clasificación avanzada',
    description: 'Clasificación con comparativa entre puntos, franjas horarias y acumulados.',
    icon: 'mdi-chart-box-multiple-outline',
    view: lazy(() => import('./classification/ClassificationAdvancedTemplate.vue')),
    datamodels: ['flowObserved', 'peopleCount'],
  },
  heatmap: {
    key: 'heatmap',
    family: 'occupancy',
    label: 'Aforo · Mapa de calor',
    description: 'Intensidad de ocupación por hora y día de la semana, y mapa de densidad.',
    icon: 'mdi-grid',
    view: lazy(() => import('./heatmap/HeatmapTemplate.vue')),
    datamodels: ['flowObserved', 'peopleCount'],
  },
  transits: {
    key: 'transits',
    family: 'occupancy',
    label: 'Aforo · Tránsitos',
    description: 'Desplazamientos entre puntos de medida, con origen, destino y volumen.',
    icon: 'mdi-transit-connection-variant',
    view: lazy(() => import('./transits/TransitsTemplate.vue')),
    datamodels: ['flowObserved', 'flowEvent'],
  },
  transitsAdvanced: {
    key: 'transitsAdvanced',
    family: 'occupancy',
    label: 'Aforo · Tránsitos avanzado',
    description: 'Tránsitos con matriz origen-destino, rutas principales y evolución.',
    icon: 'mdi-vector-polyline',
    view: lazy(() => import('./transits/TransitsAdvancedTemplate.vue')),
    datamodels: ['flowObserved', 'flowEvent'],
  },
  lidarHeatmap: {
    key: 'lidarHeatmap',
    family: 'lidar',
    label: 'Zona LIDAR · Mapa de calor',
    description: 'Densidad de ocupación en vivo sobre la zona monitorizada.',
    icon: 'mdi-map-marker-radius-outline',
    view: lazy(() => import('./lidar/LidarHeatmapTemplate.vue')),
    datamodels: ['zone'],
  },
  lidarPrediction: {
    key: 'lidarPrediction',
    family: 'lidar',
    label: 'Zona LIDAR · Predicción',
    description: 'Ocupación prevista frente a la medida, con banda de confianza.',
    icon: 'mdi-chart-timeline-variant-shimmer',
    view: lazy(() => import('./lidar/LidarPredictionTemplate.vue')),
    datamodels: ['zone', 'zonePrediction'],
  },
  lidarAnalytics: {
    key: 'lidarAnalytics',
    family: 'lidar',
    label: 'Zona LIDAR · Analítica',
    description: 'Indicadores de la zona: ocupación, aforo, permanencia y series históricas.',
    icon: 'mdi-view-dashboard-variant-outline',
    view: lazy(() => import('./lidar/LidarAnalyticsTemplate.vue')),
    datamodels: ['zone'],
  },
}

export const FAMILY_LABEL: Record<TemplateFamily, string> = {
  occupancy: 'Aforo y flujo de personas',
  lidar: 'Zonas LIDAR',
}

export function templateList(): TemplateDescriptor[] {
  return Object.values(TEMPLATES).filter((item): item is TemplateDescriptor => !!item)
}

/**
 * Devuelve la plantilla que corresponde a un cuadro guardado, o null si su tipo no esta
 * soportado en esta edicion. El null es un camino previsto: la vista muestra un aviso en
 * lugar de quedarse en blanco.
 */
export function resolveTemplate(typeId?: string | null): TemplateDescriptor | null {
  const key = keyOfTypeId(typeId)
  return (key && TEMPLATES[key]) || null
}

/** Nombres literales de modelo de datos de una plantilla, para filtrar entidades. */
export function datamodelNames(descriptor: TemplateDescriptor): string[] {
  return datamodelsOf(descriptor.datamodels)
}

export { typeIdOf, datamodelsOf }
