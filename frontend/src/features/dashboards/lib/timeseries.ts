/**
 * Forma cruda de la respuesta de `/timeseries` y coercion numerica de sus lecturas.
 *
 * El servicio de datos devuelve un array de sobres, cada uno con `time_series[]`, y cada serie
 * con `values[]` de `{ timestamp, value }`. Esa forma se reimplementaba en cada consumidor
 * (plantillas, historico de entidad, paneles) con tipos identicos y un parser de valores casi
 * igual; aqui viven la unica copia de los tipos y del parser comun.
 *
 * Lo que NO se unifica es la lectura del `timestamp`: cada consumidor lo normaliza a su manera
 * (cadena cruda, `parseApiDateTime`, `isoOf`) segun lo que necesite pintar, y esa diferencia es
 * intencionada.
 */

/** Una lectura suelta: marca y valor sin tipar, tal y como llegan del servicio. */
export interface RawValue {
  timestamp?: string
  value?: unknown
}

/** Una serie: identificador de dispositivo y medida, mas sus lecturas. */
export interface RawTimeSeries {
  device_id?: string
  measure_id?: string
  values?: RawValue[]
}

/** El sobre que envuelve las series de una sub-peticion. */
export interface RawTimeSeriesResponse {
  time_series?: RawTimeSeries[]
}

/**
 * Convierte el valor crudo de una lectura a numero, o null si no representa uno.
 *
 *  - Numero: se conserva solo si es finito (NaN/Infinity → null).
 *  - Booleano: true → 1, false → 0. Una lectura booleana (p. ej. presencia) es cuantificable.
 *  - Cadena: se parsea si tiene contenido no vacio; en blanco o no numerica → null.
 *  - Cualquier otra cosa (null, undefined, objeto) → null.
 */
export function numericValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'boolean') return value ? 1 : 0
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}
