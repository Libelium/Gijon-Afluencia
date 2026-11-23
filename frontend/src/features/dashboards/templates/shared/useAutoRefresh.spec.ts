import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, type Ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useAutoRefresh } from './useAutoRefresh'

const STORAGE_KEY = 'iris360-dashboard-auto-refresh'

/** Monta un host mínimo que solo usa el composable y expone su estado y el espía del tick. */
function mountAutoRefresh(paused: () => boolean = () => false) {
  const onTick = vi.fn()
  let enabled: Ref<boolean> | undefined
  const Host = defineComponent({
    setup() {
      enabled = useAutoRefresh(onTick, paused).enabled
      return () => h('div')
    },
  })
  const wrapper = mount(Host)
  return { onTick, enabled: enabled!, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useAutoRefresh', () => {
  it('arranca desactivado y no refresca solo', () => {
    const { onTick, enabled } = mountAutoRefresh()
    expect(enabled.value).toBe(false)
    vi.advanceTimersByTime(30 * 60_000)
    expect(onTick).not.toHaveBeenCalled()
  })

  it('al activarlo refresca cada minuto', async () => {
    const { onTick, enabled } = mountAutoRefresh()
    enabled.value = true
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(2)
  })

  it('al desactivarlo deja de refrescar', async () => {
    const { onTick, enabled } = mountAutoRefresh()
    enabled.value = true
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
    enabled.value = false
    await nextTick()
    vi.advanceTimersByTime(5 * 60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
  })

  it('no refresca mientras paused() es cierto (carga en curso o rango fijo)', async () => {
    let paused = true
    const { onTick, enabled } = mountAutoRefresh(() => paused)
    enabled.value = true
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).not.toHaveBeenCalled()
    paused = false
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
  })

  it('no refresca con la pestaña oculta', async () => {
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    const { onTick, enabled } = mountAutoRefresh()
    enabled.value = true
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).not.toHaveBeenCalled()
    hidden.mockReturnValue(false)
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
  })

  it('persiste la elección y la recupera al volver a montar', async () => {
    const first = mountAutoRefresh()
    first.enabled.value = true
    await nextTick()
    expect(localStorage.getItem(STORAGE_KEY)).toBe('on')

    const second = mountAutoRefresh()
    expect(second.enabled.value).toBe(true)
  })

  it('deja de refrescar al desmontar el panel', async () => {
    const { onTick, enabled, wrapper } = mountAutoRefresh()
    enabled.value = true
    await nextTick()
    wrapper.unmount()
    vi.advanceTimersByTime(5 * 60_000)
    expect(onTick).toHaveBeenCalledTimes(0)
  })
})
