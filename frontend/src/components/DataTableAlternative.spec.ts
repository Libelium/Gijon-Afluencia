import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTableAlternative from './DataTableAlternative.vue'
import type { AlternativeTable } from '@/features/dashboards/charts/a11y'

/**
 * Comprobaciones sobre el marcado que hace accesible la alternativa (WCAG 1.1.1 y 1.3.1).
 * Son exactamente los atributos que la auditoria echa en falta en las tablas de Vuetify:
 * `scope` en las cabeceras y un `<caption>` que diga de que es la tabla.
 */

const TABLE: AlternativeTable = {
  columns: ['Fecha y hora', 'Entrada', 'Salida'],
  rows: [
    ['01/01/2026 00:00', '5', '3'],
    ['01/01/2026 01:00', '7', '2'],
  ],
  total: 2,
}

// VIcon no esta registrado en el montaje aislado: se sustituye por un elemento inerte.
const global = { stubs: { VIcon: true } }

describe('DataTableAlternative', () => {
  it('pinta una tabla nativa, no un div con aspecto de tabla', () => {
    const wrapper = mount(DataTableAlternative, { props: { title: 'Aforo', table: TABLE }, global })
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  })

  it('cada cabecera de columna lleva scope="col"', () => {
    const wrapper = mount(DataTableAlternative, { props: { title: 'Aforo', table: TABLE }, global })
    const headers = wrapper.findAll('thead th')
    expect(headers).toHaveLength(3)
    for (const header of headers) expect(header.attributes('scope')).toBe('col')
    expect(headers.map((h) => h.text())).toEqual(TABLE.columns)
  })

  it('la primera celda de cada fila es cabecera de fila, para que el lector la repita', () => {
    const wrapper = mount(DataTableAlternative, { props: { title: 'Aforo', table: TABLE }, global })
    const rowHeaders = wrapper.findAll('tbody th')
    expect(rowHeaders).toHaveLength(2)
    for (const header of rowHeaders) expect(header.attributes('scope')).toBe('row')
    expect(rowHeaders[0].text()).toBe('01/01/2026 00:00')
  })

  it('el titulo de la grafica identifica la tabla en su <caption>', () => {
    const wrapper = mount(DataTableAlternative, { props: { title: 'Aforo', table: TABLE }, global })
    const caption = wrapper.find('caption')
    expect(caption.exists()).toBe(true)
    expect(caption.text()).toContain('Aforo')
  })

  it('el control de despliegue es un <summary> nativo: enfocable y operable con teclado', () => {
    const wrapper = mount(DataTableAlternative, { props: { title: 'Aforo', table: TABLE }, global })
    const summary = wrapper.find('summary')
    expect(summary.exists()).toBe(true)
    expect(summary.text()).toContain('Ver los datos en una tabla')
  })

  it('avisa cuando la tabla esta recortada, en lugar de dar por completo lo que no lo esta', () => {
    const wrapper = mount(DataTableAlternative, {
      props: { title: 'Aforo', table: { ...TABLE, total: 500 } },
      global,
    })
    const caption = wrapper.find('caption').text()
    expect(caption).toContain('2')
    expect(caption).toContain('500')
  })

  it('sin filas dice que no hay datos, en vez de dejar una tabla vacia', () => {
    const wrapper = mount(DataTableAlternative, {
      props: { title: 'Aforo', table: { columns: [], rows: [], total: 0 } },
      global,
    })
    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.text()).toContain('No hay datos que representar')
  })

  it('admite un texto propio para el control de despliegue', () => {
    const wrapper = mount(DataTableAlternative, {
      props: { title: 'Mapa', table: TABLE, label: 'Ver los puntos del mapa en una tabla' },
      global,
    })
    expect(wrapper.find('summary').text()).toContain('Ver los puntos del mapa en una tabla')
  })
})
