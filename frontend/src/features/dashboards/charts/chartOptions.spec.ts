import { describe, expect, it } from 'vitest'
import {
  asItems,
  axisValue,
  categoryLabel,
  chartGrid,
  chartStyle,
  dashFor,
  escapeHtml,
  hasData,
  lastPoint,
  niceCeil,
  nonNull,
  scrollLegend,
  spanOf,
  stepOf,
  timeFormatFor,
  timeFormatOf,
  timeLabel,
  toMillis,
  tooltipHeader,
  tooltipRow,
  valueAxis,
} from './chartOptions'
import type { ChartSeries } from './types'

const HOUR = 3600 * 1000
const DAY = 24 * HOUR

const serie = (name: string, points: [string, number | null][]): ChartSeries => ({
  name,
  points: points.map(([t, v]) => ({ t, v })),
})

describe('toMillis', () => {
  it('interpreta la marca del backend como UTC', () => {
    expect(toMillis('2026-01-01T00:00:00')).toBe(Date.UTC(2026, 0, 1))
  })

  it('respeta el desplazamiento cuando la cadena lo trae', () => {
    expect(toMillis('2026-01-01T01:00:00+01:00')).toBe(Date.UTC(2026, 0, 1))
  })

  it('devuelve NaN con una cadena que no es una fecha, en vez de una fecha inventada', () => {
    expect(Number.isNaN(toMillis('lunes'))).toBe(true)
    expect(Number.isNaN(toMillis(''))).toBe(true)
  })
})

describe('nonNull / lastPoint / hasData', () => {
  const s = serie('a', [
    ['2026-01-01T00:00:00', 1],
    ['2026-01-01T01:00:00', null],
    ['2026-01-01T02:00:00', 3],
  ])

  it('descarta nulos y valores no finitos', () => {
    expect(nonNull(s.points)).toHaveLength(2)
    expect(nonNull([{ t: 'x', v: Number.NaN }])).toHaveLength(0)
    expect(nonNull([{ t: 'x', v: Number.POSITIVE_INFINITY }])).toHaveLength(0)
  })

  it('el ultimo punto es el ultimo CON valor, no el ultimo del array', () => {
    expect(lastPoint(s)?.v).toBe(3)
    expect(lastPoint(serie('b', [['2026-01-01T00:00:00', null]]))).toBeNull()
    expect(lastPoint(undefined)).toBeNull()
  })

  it('hasData distingue "sin serie" de "serie sin lecturas"', () => {
    expect(hasData([])).toBe(false)
    expect(hasData([serie('b', [['2026-01-01T00:00:00', null]])])).toBe(false)
    expect(hasData([s])).toBe(true)
  })
})

describe('spanOf y stepOf', () => {
  it('la amplitud abarca todas las series', () => {
    const span = spanOf([
      serie('a', [['2026-01-01T00:00:00', 1]]),
      serie('b', [['2026-01-03T00:00:00', 1]]),
    ])
    expect(span).toBe(2 * DAY)
  })

  it('la amplitud es 0 con un solo instante o sin datos', () => {
    expect(spanOf([])).toBe(0)
    expect(spanOf([serie('a', [['2026-01-01T00:00:00', 1]])])).toBe(0)
  })

  it('el paso es la MEDIANA de los huecos, no el minimo', () => {
    // Serie diaria con un par de lecturas seguidas. El minimo seria un minuto y el eje se
    // rotularia con horas; la mediana es casi un dia, que es la lectura correcta.
    const s = serie('a', [
      ['2026-01-01T00:00:00', 1],
      ['2026-01-01T00:01:00', 1],
      ['2026-01-02T00:00:00', 1],
      ['2026-01-03T00:00:00', 1],
    ])
    const step = stepOf([s])
    expect(step).toBeGreaterThan(20 * HOUR)
    expect(step).toBeLessThanOrEqual(DAY)
    // Y con ese paso el eje elige formato de fecha, no de hora.
    expect(timeFormatFor(spanOf([s]), false, step)).toBe('dd/MM')
  })

  it('el paso es 0 si no hay dos instantes distintos', () => {
    expect(stepOf([serie('a', [['2026-01-01T00:00:00', 1]])])).toBe(0)
  })
})

describe('timeFormatFor', () => {
  it('con lecturas diarias rotula la fecha, aunque la amplitud sea corta', () => {
    // El motivo de que el paso mande sobre la amplitud: con datos diarios la hora es 00:00 en
    // todos los puntos y dos fechas distintas quedarian rotuladas igual.
    expect(timeFormatFor(3 * DAY, false, DAY)).toBe('dd/MM')
  })

  it('con lecturas diarias y mas de cien dias pasa a mes y ano', () => {
    expect(timeFormatFor(200 * DAY, false, DAY)).toBe('MM/yyyy')
  })

  it.each([
    [12 * HOUR, 'HH:mm'],
    [3 * DAY, 'dd/MM HH:mm'],
    [30 * DAY, 'dd/MM'],
    [200 * DAY, 'MM/yyyy'],
  ])('con amplitud %i usa %s', (span, expected) => {
    expect(timeFormatFor(span, false, 0)).toBe(expected)
  })

  it('en pantalla estrecha recorta la hora en el rango semanal', () => {
    expect(timeFormatFor(3 * DAY, true, 0)).toBe('dd/MM')
  })

  it('timeFormatOf deduce amplitud y paso de la propia serie', () => {
    const s = serie('a', [
      ['2026-01-01T00:00:00', 1],
      ['2026-01-02T00:00:00', 1],
      ['2026-01-03T00:00:00', 1],
    ])
    expect(timeFormatOf([s])).toBe('dd/MM')
  })
})

describe('timeLabel y categoryLabel', () => {
  it('imprime la marca en la zona del usuario, no en la del navegador', () => {
    const ms = Date.UTC(2026, 0, 1, 23, 0)
    expect(timeLabel(ms, 'UTC', 'dd/MM HH:mm')).toBe('01/01 23:00')
    expect(timeLabel(ms, 'Europe/Madrid', 'dd/MM HH:mm')).toBe('02/01 00:00')
  })

  it('devuelve un guion con una zona invalida en lugar de romper el eje', () => {
    expect(timeLabel(Date.UTC(2026, 0, 1), 'No/Existe', 'dd/MM')).toBe('—')
  })

  it('categoryLabel deja pasar el texto que no es una fecha', () => {
    expect(categoryLabel('Entrada norte', 'UTC', 'dd/MM')).toBe('Entrada norte')
    expect(categoryLabel('2026-01-01T00:00:00', 'UTC', 'dd/MM')).toBe('01/01')
  })
})

describe('axisValue', () => {
  it('abrevia a partir de cien mil', () => {
    expect(axisValue(1_500_000)).toMatch(/1,5\s?M/)
  })

  it('quita decimales en los millares y los conserva en las cifras pequenas', () => {
    expect(axisValue(1234)).toBe('1234')
    expect(axisValue(12.345)).toBe('12,3')
    expect(axisValue(1.234)).toBe('1,23')
  })

  it('devuelve un guion con un valor no finito', () => {
    expect(axisValue(Number.NaN)).toBe('—')
    expect(axisValue(Number.POSITIVE_INFINITY)).toBe('—')
  })
})

describe('dashFor', () => {
  it('con menos de cuatro series el color basta y todas van continuas', () => {
    expect(dashFor(0, 3)).toBe('solid')
    expect(dashFor(2, 3)).toBe('solid')
  })

  it('a partir de cuatro refuerza cada serie con un trazo distinto', () => {
    // Es lo que permite distinguirlas sin depender del color (WCAG 1.4.1).
    const patterns = [0, 1, 2, 3].map((i) => JSON.stringify(dashFor(i, 4)))
    expect(new Set(patterns).size).toBe(4)
  })

  it('el patron se repite ciclicamente por encima de cuatro series', () => {
    expect(dashFor(4, 6)).toEqual(dashFor(0, 6))
  })
})

describe('escapeHtml y las filas del globo', () => {
  it('escapa lo que podria cerrar una etiqueta', () => {
    expect(escapeHtml('<img src=x onerror="alert(1)">')).toBe(
      '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;',
    )
  })

  it('el nombre de serie que llega del backend no puede inyectar HTML en el globo', () => {
    const row = tooltipRow('', '<b>bold</b>', '1')
    expect(row).not.toContain('<b>bold</b>')
    expect(row).toContain('&lt;b&gt;bold&lt;/b&gt;')
  })

  it('la cabecera del globo tambien escapa', () => {
    expect(tooltipHeader('<script>')).toContain('&lt;script&gt;')
  })
})

describe('niceCeil', () => {
  it('deja aire por encima del valor', () => {
    expect(niceCeil(95)).toBeGreaterThanOrEqual(95 * 1.05)
    expect(niceCeil(1)).toBeGreaterThanOrEqual(1.05)
  })

  it('devuelve 100 con valores que no sirven de techo', () => {
    expect(niceCeil(0)).toBe(100)
    expect(niceCeil(-5)).toBe(100)
    expect(niceCeil(Number.NaN)).toBe(100)
  })

  it('elige un numero redondo, no el valor exacto', () => {
    expect(niceCeil(830)).toBe(1000)
    expect(niceCeil(230)).toBe(250)
  })
})

describe('asItems', () => {
  it('acepta tanto un objeto como una lista', () => {
    expect(asItems({ seriesName: 'a' })).toHaveLength(1)
    expect(asItems([{ seriesName: 'a' }, { seriesName: 'b' }])).toHaveLength(2)
  })
})

/** COD-098: fragmentos que estaban copiados en cuatro graficos. */
describe('fragmentos de opciones compartidos', () => {
  // El tipo de ECharts para un eje es la union de todas sus variantes, y `splitNumber` solo
  // existe en la de valores: se estrecha aqui en vez de en la funcion, que devuelve el tipo
  // que la biblioteca espera recibir.
  const axis = (compact: boolean, min?: number) =>
    valueAxis(compact, min) as { splitNumber?: number; min?: number }

  it('el eje de valores reduce las marcas en pantalla estrecha', () => {
    expect(axis(false).splitNumber).toBe(5)
    expect(axis(true).splitNumber).toBe(3)
  })

  it('el eje de valores admite un suelo explicito', () => {
    expect(axis(false, 0).min).toBe(0)
    expect(axis(false).min).toBeUndefined()
  })

  it('la rejilla solo varia en el margen inferior', () => {
    expect(chartGrid(34)).toEqual({ left: 8, right: 20, top: 20, bottom: 34, containLabel: true })
  })

  it('la leyenda se puede ocultar y admite una lista explicita de series', () => {
    expect(scrollLegend(false).show).toBe(false)
    expect(scrollLegend(true, ['a']).data).toEqual(['a'])
  })

  it('el estilo del lienzo interpreta un numero como pixeles y respeta una cadena', () => {
    expect(chartStyle(280)).toEqual({ height: '280px', width: '100%' })
    expect(chartStyle('50vh')).toEqual({ height: '50vh', width: '100%' })
  })
})
