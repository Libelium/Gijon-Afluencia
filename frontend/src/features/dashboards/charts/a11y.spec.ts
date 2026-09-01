import { describe, expect, it } from 'vitest'
import { ariaOption, MAX_ALTERNATIVE_ROWS, pairsTable, rowsTable, seriesTable, stampLabel } from './a11y'
import type { ChartSeries } from './types'

/**
 * Estas pruebas cubren la alternativa textual de las graficas (WCAG 1.1.1, hallazgo
 * GDTIS-PT01-ACC-002). Lo que se comprueba no es «que salga una tabla», sino que la tabla sea
 * EQUIVALENTE: que no pierda puntos, que no invente filas y que sus cabeceras identifiquen la
 * serie y su unidad.
 */

const serie = (name: string, points: [string, number | null][], units?: string): ChartSeries => ({
  name,
  units,
  points: points.map(([t, v]) => ({ t, v })),
})

const OPTIONS = { timeZone: 'UTC' }

describe('seriesTable', () => {
  it('la primera columna es el instante y despues va una columna por serie', () => {
    const table = seriesTable(
      [serie('Entrada', [['2026-01-01T00:00:00', 5]]), serie('Salida', [['2026-01-01T00:00:00', 3]])],
      OPTIONS,
    )
    expect(table.columns).toEqual(['Fecha y hora', 'Entrada', 'Salida'])
    expect(table.rows).toEqual([['01/01/2026 00:00', '5', '3']])
  })

  it('la unidad va en la cabecera, no repetida en cada celda', () => {
    const table = seriesTable([serie('Aforo', [['2026-01-01T00:00:00', 5]], 'personas')], OPTIONS)
    expect(table.columns[1]).toBe('Aforo (personas)')
    expect(table.rows[0][1]).toBe('5')
  })

  it('la unidad general se aplica a la serie que no trae la suya', () => {
    const table = seriesTable([serie('Aforo', [['2026-01-01T00:00:00', 5]])], {
      ...OPTIONS,
      units: '%',
    })
    expect(table.columns[1]).toBe('Aforo (%)')
  })

  it('une las marcas de series que no coinciden y deja hueco donde no hay lectura', () => {
    const table = seriesTable(
      [
        serie('A', [
          ['2026-01-01T00:00:00', 1],
          ['2026-01-01T02:00:00', 3],
        ]),
        serie('B', [['2026-01-01T01:00:00', 2]]),
      ],
      OPTIONS,
    )
    expect(table.rows.map((row) => row[0])).toEqual([
      '01/01/2026 00:00',
      '01/01/2026 01:00',
      '01/01/2026 02:00',
    ])
    // El hueco se marca con el guion de «sin valor», no con un cero, que seria un dato falso.
    expect(table.rows[1]).toEqual(['01/01/2026 01:00', '—', '2'])
  })

  it('descarta las marcas donde ninguna serie tiene lectura', () => {
    const table = seriesTable([serie('A', [['2026-01-01T00:00:00', null]])], OPTIONS)
    expect(table.rows).toHaveLength(0)
    expect(table.total).toBe(0)
  })

  it('ordena de forma ascendente por defecto: se lee como el grafico, de izquierda a derecha', () => {
    const table = seriesTable(
      [
        serie('A', [
          ['2026-01-02T00:00:00', 2],
          ['2026-01-01T00:00:00', 1],
        ]),
      ],
      OPTIONS,
    )
    expect(table.rows.map((row) => row[1])).toEqual(['1', '2'])
  })

  it('con order: desc pone lo mas reciente arriba', () => {
    const table = seriesTable(
      [
        serie('A', [
          ['2026-01-01T00:00:00', 1],
          ['2026-01-02T00:00:00', 2],
        ]),
      ],
      { ...OPTIONS, order: 'desc' },
    )
    expect(table.rows.map((row) => row[1])).toEqual(['2', '1'])
  })

  it('imprime el instante en la zona horaria del usuario', () => {
    const table = seriesTable([serie('A', [['2026-01-01T23:00:00', 1]])], {
      timeZone: 'Europe/Madrid',
    })
    expect(table.rows[0][0]).toBe('02/01/2026 00:00')
  })

  it('acepta categorias que no son fechas y las deja tal cual', () => {
    const table = seriesTable([serie('A', [['Entrada norte', 7]])], OPTIONS)
    expect(table.rows[0][0]).toBe('Entrada norte')
  })

  it('recorta a un tope y deja constancia del total, para poder avisar de que falta', () => {
    const points: [string, number][] = Array.from({ length: 250 }, (_, i) => [
      `2026-01-01T${String(i % 24).padStart(2, '0')}:${String(Math.floor(i / 24)).padStart(2, '0')}:00`,
      i,
    ])
    const table = seriesTable([serie('A', points)], OPTIONS)
    expect(table.rows).toHaveLength(MAX_ALTERNATIVE_ROWS)
    expect(table.total).toBe(250)
  })

  it('sin series devuelve una tabla vacia, no una tabla con cabeceras y nada debajo', () => {
    const table = seriesTable([], OPTIONS)
    expect(table.columns).toHaveLength(0)
    expect(table.rows).toHaveLength(0)
  })
})

describe('pairsTable y rowsTable', () => {
  it('pairsTable conserva el orden de llegada', () => {
    const table = pairsTable(
      [
        { label: 'Norte', value: '10' },
        { label: 'Sur', value: '4' },
      ],
      ['Zona', 'Valor'],
    )
    expect(table.columns).toEqual(['Zona', 'Valor'])
    expect(table.rows).toEqual([
      ['Norte', '10'],
      ['Sur', '4'],
    ])
    expect(table.total).toBe(2)
  })

  it('rowsTable recorta pero informa del total', () => {
    const rows = Array.from({ length: 5 }, (_, i) => [String(i), 'x'])
    const table = rowsTable(['a', 'b'], rows, 2)
    expect(table.rows).toHaveLength(2)
    expect(table.total).toBe(5)
  })
})

describe('stampLabel', () => {
  it('formatea lo que es una fecha y respeta lo que no', () => {
    expect(stampLabel('2026-01-01T00:00:00', 'UTC')).toBe('01/01/2026 00:00')
    expect(stampLabel('Entrada norte', 'UTC')).toBe('Entrada norte')
  })
})

describe('ariaOption', () => {
  it('activa el modulo aria de ECharts, que es lo que da nombre al lienzo', () => {
    const aria = ariaOption('Ocupación media')
    expect(aria.enabled).toBe(true)
    expect(aria.label?.enabled).toBe(true)
  })

  it('la descripcion nombra la grafica y remite a la tabla, en vez de describir el dibujo', () => {
    const description = ariaOption('Ocupación media').label?.description ?? ''
    expect(description).toContain('Ocupación media')
    expect(description).toContain('tabla')
  })
})
