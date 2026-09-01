import { afterEach, describe, expect, it } from 'vitest'
import * as echarts from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { AriaComponent, GridComponent } from 'echarts/components'
import { ariaOption } from './a11y'

/**
 * Comprobacion de que el modulo `aria` de ECharts hace lo que se espera de el: poner
 * `role="img"` y un nombre accesible en el contenedor del lienzo (WCAG 1.1.1, hallazgo
 * GDTIS-PT01-ACC-002, y WCAG 4.1.2 para el nombre).
 *
 * Se renderiza con SVG y no con lienzo porque jsdom no implementa `canvas.getContext`, y el
 * modulo `aria` es independiente del renderizador: escribe sobre el DOM del contenedor, no
 * sobre lo dibujado. Lo que se verifica —que activar la opcion basta para que aparezcan los
 * atributos— es exactamente lo mismo en los dos casos.
 *
 * Sirve ademas de red frente a una actualizacion de ECharts: si el modulo dejara de instalarse
 * o cambiara de comportamiento, los graficos volverian a ser un lienzo sin nombre y aqui se
 * veria.
 */

echarts.use([SVGRenderer, LineChart, GridComponent, AriaComponent])

const instances: echarts.ECharts[] = []

function render(option: Record<string, unknown>): HTMLElement {
  const el = document.createElement('div')
  document.body.appendChild(el)
  const chart = echarts.init(el, undefined, { renderer: 'svg', width: 600, height: 300 })
  instances.push(chart)
  chart.setOption(option)
  return el
}

const SERIES = {
  xAxis: { type: 'category', data: ['a', 'b', 'c'] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', name: 'Aforo', data: [1, 2, 3] }],
}

afterEach(() => {
  while (instances.length) instances.pop()?.dispose()
  document.body.innerHTML = ''
})

describe('modulo aria de ECharts', () => {
  it('sin activarlo, el contenedor del grafico no tiene ni rol ni nombre', () => {
    // Este es el estado que encontro la auditoria en las nueve graficas.
    const el = render(SERIES)
    expect(el.getAttribute('role')).toBeNull()
    expect(el.getAttribute('aria-label')).toBeNull()
  })

  it('con ariaOption() el contenedor pasa a ser una imagen con nombre', () => {
    const el = render({ ...SERIES, aria: ariaOption('Ocupación media') })
    expect(el.getAttribute('role')).toBe('img')
    expect(el.getAttribute('aria-label')).toContain('Ocupación media')
  })

  it('el nombre remite a la tabla equivalente en lugar de describir el dibujo', () => {
    const el = render({ ...SERIES, aria: ariaOption('Ocupación media') })
    expect(el.getAttribute('aria-label')).toContain('tabla')
  })
})
