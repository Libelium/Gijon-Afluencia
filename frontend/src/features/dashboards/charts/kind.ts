import type { Panel } from '@/types'
import type { ChartKind } from './types'

/**
 * Los paneles se crearon con otra herramienta y su `chart.type` trae una nomenclatura ajena,
 * con docenas de variantes ("linear", "column", "tile", "matrix", "stackedBar"...). Una tabla
 * de equivalencias exactas se rompe en cuanto aparece un tipo nuevo, asi que se busca por
 * fragmentos: lo que no encaje cae en 'unsupported' y la pantalla sigue funcionando.
 *
 * El orden importa — se devuelve la primera familia que coincida — y ampliarlo es anadir
 * un fragmento a la lista correspondiente.
 */
const PATTERNS: [ChartKind, string[]][] = [
  ['line', ['line', 'linear', 'area', 'step', 'spline', 'trend', 'linea']],
  ['bar', ['bar', 'column', 'histogram', 'barra', 'columna']],
  ['pie', ['pie', 'donut', 'doughnut', 'tarta', 'sector']],
  ['gauge', ['gauge', 'battery', 'dial', 'bateria', 'aguja']],
  ['kpi', ['kpi', 'tile', 'text', 'value', 'single', 'metric', 'cifra', 'valor']],
  ['table', ['table', 'matrix', 'tabla']],
]

function match(raw: unknown): ChartKind | null {
  if (raw === null || raw === undefined) return null
  const text = String(raw).toLowerCase()
  if (!text) return null
  for (const [kind, fragments] of PATTERNS) {
    if (fragments.some((fragment) => text.includes(fragment))) return kind
  }
  return null
}

/** El tipo manda; el titulo solo se consulta cuando el tipo no dice nada reconocible. */
export function resolveChartKind(panel: Panel): ChartKind {
  const forced = new URLSearchParams(location.search).get('kind') as ChartKind | null
  if (forced) return forced
  return match(panel.chart?.type) ?? match(panel.chart?.title) ?? 'unsupported'
}

const has = (panel: Panel, fragment: string) =>
  String(panel.chart?.type ?? '').toLowerCase().includes(fragment)

/**
 * Matices del tipo original que si merece la pena respetar al dibujar: un «area» rellena y un
 * «stacked» apila. No cambian la familia de grafico, solo como se pinta.
 */
export function chartVariant(panel: Panel) {
  return { area: has(panel, 'area'), stacked: has(panel, 'stack') }
}
