import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { Dashboard, Entity, Measure } from '@/types'
import { datamodelOf } from '../contract'
import { useZone, type UseZone } from './useZone'

const { getEntityMeasures, fetchTemplateEntities } = vi.hoisted(() => ({
  getEntityMeasures: vi.fn(),
  fetchTemplateEntities: vi.fn(),
}))

vi.mock('@/features/entities/api/entities', () => ({ getEntityMeasures, listEntities: vi.fn() }))
vi.mock('./data', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./data')>()),
  fetchTemplateEntities,
}))

const zone = (id: number, tail: string): Entity => {
  const datamodel = datamodelOf('zone')
  return { id, name: tail, urn: `urn:ngsi-ld:${datamodel}:${tail}`, datamodel, tenant: 'demo', scope: '/' }
}

const occupancy = (value: number): Measure[] => [{ id: 'occupancy', name: 'occupancy', value }]

/** Monta un componente minimo que solo usa el composable y lo devuelve. */
async function mountZone(): Promise<UseZone> {
  let state: UseZone | undefined
  const Host = defineComponent({
    setup() {
      state = useZone({ dashboard: { id: 1 } as Dashboard })
      return () => h('div')
    },
  })
  mount(Host, { global: { plugins: [createPinia()] } })
  await flushPromises()
  return state!
}

beforeEach(() => {
  getEntityMeasures.mockReset()
  fetchTemplateEntities.mockReset()
  fetchTemplateEntities.mockResolvedValue([zone(1, 'P01'), zone(2, 'P02'), zone(3, 'P03')])
})

describe('useZone', () => {
  it('al montar carga las zonas y las medidas de la primera', async () => {
    getEntityMeasures.mockResolvedValue(occupancy(45))
    const z = await mountZone()
    expect(z.zones.value.map((e) => e.id)).toEqual([1, 2, 3])
    expect(z.zoneId.value).toBe(1)
    expect(z.profile.value?.current).toBe(45)
    expect(getEntityMeasures).toHaveBeenCalledTimes(1)
  })

  it('un rango personalizado manda sobre el preajuste, y al borrarlo vuelve el preajuste', async () => {
    getEntityMeasures.mockResolvedValue(occupancy(45))
    const z = await mountZone()
    const custom = { start: '2026-10-19T22:00:00Z', end: '2026-10-27T23:00:00Z' }
    z.custom.value = custom
    expect(z.range.value).toEqual(custom)
    z.custom.value = null
    expect(z.range.value).not.toEqual(custom)
  })

  it('si falla el cambio de zona lo dice y no deja los datos de la anterior', async () => {
    getEntityMeasures.mockResolvedValueOnce(occupancy(45))
    const z = await mountZone()

    getEntityMeasures.mockRejectedValueOnce(new Error('sin red'))
    z.zoneId.value = 2
    await flushPromises()

    expect(z.error.value).toBeTruthy()
    expect(z.measures.value).toEqual([])
  })

  it('una respuesta que llega tarde no pisa la de la zona elegida despues', async () => {
    getEntityMeasures.mockResolvedValueOnce(occupancy(45))
    const z = await mountZone()

    let releaseSlow: (value: Measure[]) => void = () => {}
    getEntityMeasures.mockReturnValueOnce(new Promise((resolve) => (releaseSlow = resolve)))
    getEntityMeasures.mockResolvedValueOnce(occupancy(7))

    z.zoneId.value = 2
    await flushPromises()
    z.zoneId.value = 3
    await flushPromises()
    releaseSlow(occupancy(99))
    await flushPromises()

    expect(z.profile.value?.current).toBe(7)
  })
})
