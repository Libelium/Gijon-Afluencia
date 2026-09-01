import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { VDataTable, VDataTableServer } from 'vuetify/components'
import ConfirmDialog from '@/features/dashboards/components/ConfirmDialog.vue'
import vuetify from './vuetify'

/**
 * Verificacion del hallazgo GDTIS-PT01-ACC-006 sobre el render REAL de Vuetify.
 *
 * La correccion es una linea de configuracion (`headerProps: { scope: 'col' }` en los valores
 * por defecto), y todo depende de un detalle interno de la biblioteca: que `headerProps` acabe
 * como atributo del `<th>`. Comprobarlo leyendo el codigo de Vuetify no vale —cambia entre
 * versiones—, asi que se monta una tabla de verdad y se mira el HTML que sale. Si una
 * actualizacion de Vuetify rompe esa via, esta prueba lo dice.
 */

const HEADERS = [
  { title: 'Nombre', key: 'name', sortable: false },
  { title: 'Modelo', key: 'model', sortable: false },
]

const ITEMS = [
  { name: 'Sensor 1', model: 'Device' },
  { name: 'Sensor 2', model: 'Device' },
]

/**
 * Las props de las tablas de Vuetify son genericas sobre el tipo de fila, asi que no hay un
 * tipo comun a las dos con el que tipar este ayudante. Lo que se comprueba es el HTML que sale,
 * no la firma: se monta con las props sin comprobar y las asercion es sobre el resultado.
 */
type AnyComponent = Parameters<typeof mount>[0]

const mountTable = (component: AnyComponent, props: Record<string, unknown>) =>
  mount(component, { props, global: { plugins: [vuetify] } } as Parameters<typeof mount>[1])

describe('valores por defecto del tema', () => {
  it('VDataTable genera cada <th> de cabecera con scope="col"', () => {
    const wrapper = mountTable(VDataTable, {
      headers: HEADERS,
      items: ITEMS,
      itemsPerPage: -1,
      hideDefaultFooter: true,
    })

    const headers = wrapper.findAll('thead th')
    expect(headers.length).toBe(HEADERS.length)
    for (const header of headers) expect(header.attributes('scope')).toBe('col')
  })

  it('VDataTableServer tambien: es la tabla de los dos listados paginados', () => {
    const wrapper = mountTable(VDataTableServer, {
      headers: HEADERS,
      items: ITEMS,
      itemsLength: 2,
      itemsPerPage: -1,
      hideDefaultFooter: true,
    })

    const headers = wrapper.findAll('thead th')
    expect(headers.length).toBe(HEADERS.length)
    for (const header of headers) expect(header.attributes('scope')).toBe('col')
  })

  it('la opacidad de texto secundario del tema es la corregida, no la de serie de Vuetify', () => {
    // El valor lo comprueba `theme.spec.ts` contra el umbral de contraste; aqui solo se
    // verifica que llega efectivamente a la instancia de Vuetify.
    expect(vuetify.theme.themes.value.light.variables['medium-emphasis-opacity']).toBe(0.7)
    expect(vuetify.theme.themes.value.dark.variables['medium-emphasis-opacity']).toBe(0.7)
  })
})

/**
 * Verificacion del hallazgo GDTIS-PT01-ACC-007 sobre el render real.
 *
 * `aria-labelledby` se pasa a `VDialog` como atributo suelto y depende de un detalle interno de
 * Vuetify —que `VOverlay` fusione los atributos heredados en el mismo elemento que lleva
 * `role="dialog"`— para acabar donde tiene que estar. Se comprueba en el DOM, no leyendo la
 * biblioteca: si una version futura los separa, el dialogo volveria a anunciarse sin nombre.
 */
describe('nombre accesible de los dialogos', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('el diálogo se asocia con su título y el título existe en el documento', async () => {
    const wrapper = mount(ConfirmDialog, {
      props: { modelValue: true, title: 'Eliminar el panel' },
      global: { plugins: [vuetify] },
      attachTo: document.body,
    })
    await nextTick()

    const dialog = document.querySelector('[role="dialog"]')
    expect(dialog, 'Vuetify deberia haber pintado el dialogo').not.toBeNull()

    const labelledBy = dialog?.getAttribute('aria-labelledby')
    expect(labelledBy).toBeTruthy()

    const title = document.getElementById(labelledBy as string)
    expect(title, 'aria-labelledby debe apuntar a un elemento existente').not.toBeNull()
    expect(title?.textContent).toContain('Eliminar el panel')

    wrapper.unmount()
  })
})
