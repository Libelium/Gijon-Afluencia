import type { ChartPoint } from '../../charts'
import type { Dashboard, Entity, EntityRef } from '@/types'

/**
 * El cuadro tal y como lo recibe una plantilla. `entities` es opcional a proposito: el tipo
 * `Dashboard` del nucleo no lo declara, y la plantilla las pide por su cuenta si no llegan.
 */
export interface TemplateDashboard extends Dashboard {
  entities?: Entity[]
}

/** Punto de medida ya resuelto: identidad para pedir datos, etiqueta y coordenadas. */
export interface Point {
  /** Clave estable para v-for y para indexar respuestas. Es el URN. */
  key: string
  entity: Entity
  ref: EntityRef
  /** `entity.name` si lo hay; si no, la cola del URN. Nunca cadena vacia. */
  label: string
  lat: number | null
  lon: number | null
}

/** Una barra / un sector / una celda: clave tecnica, rotulo visible y valor. */
export interface Bucket {
  key: string
  label: string
  value: number | null
}

/** Celda de una matriz. `x` e `y` son indices en los arrays de rotulos, `y` de arriba a abajo. */
export interface MatrixCell {
  x: number
  y: number
  value: number | null
}

/** Indicadores de una serie. `null` significa «sin dato», nunca 0. */
export interface Kpis {
  current: number | null
  max: number | null
  mean: number | null
  total: number | null
  /** Marca de tiempo ISO del valor actual. */
  at: string | null
  /** Marca de tiempo ISO del maximo. */
  maxAt: string | null
}

/** Serie lista para LineChart / BarChart / PieChart / StackedAreaChart. */
export interface NamedSeries {
  name: string
  units?: string
  points: ChartPoint[]
}

export type MeasureIntent = 'occupancy' | 'transit'

export interface MeasureOption {
  value: string
  title: string
}

export interface Category {
  measureId: string
  label: string
  /** Orden estable para que el color de una categoria no baile entre recargas. */
  order: number
}
