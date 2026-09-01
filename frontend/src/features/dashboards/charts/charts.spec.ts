import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import vuetify from '@/plugins/vuetify'
import BarChart from './BarChart.vue'
import DataTableChart from './DataTableChart.vue'
import GaugeChart from './GaugeChart.vue'
import LineChart from './LineChart.vue'
import PieChart from './PieChart.vue'
import type { ChartSeries } from './types'

/**
 * Prueba de humo de los cuatro graficos de lienzo mas su version en tabla.
 *
 * Comprueba dos cosas a la vez:
 *
 *  1. Que montar el grafico con datos reales no revienta. Es la red minima que faltaba: hasta
 *     ahora un error en el objeto de opciones de ECharts solo se veia abriendo la pantalla.
 *  2. Que cada uno publica su alternativa textual con los MISMOS datos que dibuja
 *     (WCAG 1.1.1, hallazgo GDTIS-PT01-ACC-002). Es la comprobacion que impide que la
 *     alternativa se quede atras cuando se toque la grafica.
 */

const SERIES: ChartSeries[] = [
  {
    name: 'Entrada norte',
    units: 'personas',
    points: [
      { t: '2026-01-01T00:00:00', v: 10 },
      { t: '2026-01-01T01:00:00', v: 25 },
      { t: '2026-01-01T02:00:00', v: null },
      { t: '2026-01-01T03:00:00', v: 40 },
    ],
  },
]

const options = { global: { plugins: [createPinia(), vuetify] } }

/**
 * ECharts avisa por consola —no lanza— cuando una opcion no se aplica porque falta la pieza que
 * la implementa. Es exactamente lo que paso al subir a ECharts 6 con `grid.containLabel`: los
 * graficos seguian pintando, con las etiquetas de los ejes recortadas, y solo lo delataba una
 * linea de aviso. Se vigilan los dos canales y se exige silencio.
 */
const echartsMessages: string[] = []

beforeEach(() => {
  echartsMessages.length = 0
  for (const channel of ['warn', 'error', 'log'] as const) {
    vi.spyOn(console, channel).mockImplementation((...args: unknown[]) => {
      const text = args.map(String).join(' ')
      if (text.includes('[ECharts]')) echartsMessages.push(text)
    })
  }
})

afterEach(() => vi.restoreAllMocks())

const CHARTS = [
  ['LineChart', LineChart],
  ['BarChart', BarChart],
  ['PieChart', PieChart],
  ['GaugeChart', GaugeChart],
] as const

describe.each(CHARTS)('%s', (_name, component) => {
  it('se monta con datos sin lanzar y sin que ECharts se queje', () => {
    const wrapper = mount(component, { props: { series: SERIES }, ...options })
    expect(wrapper.exists()).toBe(true)
    expect(echartsMessages).toEqual([])
  })

  it('acompana la grafica con su tabla equivalente', () => {
    const wrapper = mount(component, { props: { series: SERIES }, ...options })
    const table = wrapper.find('table')
    expect(table.exists()).toBe(true)
    expect(wrapper.find('summary').exists()).toBe(true)
  })

  it('la tabla equivalente contiene los valores que se dibujan', () => {
    const wrapper = mount(component, { props: { series: SERIES }, ...options })
    const text = wrapper.find('table').text()
    for (const value of ['10', '25', '40']) expect(text).toContain(value)
  })

  it('el titulo que se le pasa nombra la grafica y encabeza la tabla', () => {
    const wrapper = mount(component, {
      props: { series: SERIES, title: 'Aforo del paseo' },
      ...options,
    })
    expect(wrapper.find('caption').text()).toContain('Aforo del paseo')
  })

  it('sin datos sigue montando y no ofrece una tabla vacia como si fuera el dato', () => {
    const wrapper = mount(component, { props: { series: [] }, ...options })
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.find('table').exists()).toBe(false)
  })
})

describe('DataTableChart', () => {
  it('pinta las lecturas con lo mas reciente arriba', () => {
    const wrapper = mount(DataTableChart, { props: { series: SERIES }, ...options })
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(3) // la lectura nula no genera fila
    // Se comprueba por el valor y no por la hora: la hora se imprime en la zona del usuario
    // (Europe/Madrid por defecto), asi que ligarla al texto haria la prueba dependiente del
    // horario de verano.
    expect(rows[0].text()).toContain('40')
    expect(rows[2].text()).toContain('10')
  })

  it('pone la unidad en la cabecera y no en cada celda', () => {
    const wrapper = mount(DataTableChart, { props: { series: SERIES }, ...options })
    const header = wrapper.find('thead').text()
    expect(header).toContain('Entrada norte (personas)')
    expect(wrapper.find('tbody').text()).not.toContain('personas')
  })

  it('sus cabeceras llevan scope="col", como el resto de tablas de la aplicacion', () => {
    const wrapper = mount(DataTableChart, { props: { series: SERIES }, ...options })
    for (const header of wrapper.findAll('thead th')) {
      expect(header.attributes('scope')).toBe('col')
    }
  })
})
