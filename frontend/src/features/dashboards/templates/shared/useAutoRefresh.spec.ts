import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, type Ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useAutoRefresh, type AutoRefreshMinutes } from './useAutoRefresh'

const STORAGE_KEY = 'iris360-dashboard-auto-refresh'

/** Monta un host mínimo que solo usa el composable y expone su estado y el espía del tick. */
function mountAutoRefresh(paused: () => boolean = () => false) {
  const onTick = vi.fn()
  let minutes: Ref<AutoRefreshMinutes> | undefined
  const Host = defineComponent({
    setup() {
      minutes = useAutoRefresh(onTick, paused).minutes
      return () => h('div')
    },
  })
  const wrapper = mount(Host)
  return { onTick, minutes: minutes!, wrapper }
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
    const { onTick, minutes } = mountAutoRefresh()
    expect(minutes.value).toBe(0)
    vi.advanceTimersByTime(30 * 60_000)
    expect(onTick).not.toHaveBeenCalled()
  })

  it('refresca cada N minutos cuando se elige una cadencia', async () => {
    const { onTick, minutes } = mountAutoRefresh()
    minutes.value = 5
    await nextTick()
    vi.advanceTimersByTime(5 * 60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5 * 60_000)
    expect(onTick).toHaveBeenCalledTimes(2)
  })

  it('no refresca mientras paused() es cierto (carga en curso o rango fijo)', async () => {
    let paused = true
    const { onTick, minutes } = mountAutoRefresh(() => paused)
    minutes.value = 1
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).not.toHaveBeenCalled()
    paused = false
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
  })

  it('no refresca con la pestaña oculta', async () => {
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    const { onTick, minutes } = mountAutoRefresh()
    minutes.value = 1
    await nextTick()
    vi.advanceTimersByTime(60_000)
    expect(onTick).not.toHaveBeenCalled()
    hidden.mockReturnValue(false)
    vi.advanceTimersByTime(60_000)
    expect(onTick).toHaveBeenCalledTimes(1)
  })

  it('persiste la elección y la recupera al volver a montar', async () => {
    const first = mountAutoRefresh()
    first.minutes.value = 10
    await nextTick()
    expect(localStorage.getItem(STORAGE_KEY)).toBe('10')

    const second = mountAutoRefresh()
    expect(second.minutes.value).toBe(10)
  })

  it('deja de refrescar al desmontar el panel', async () => {
    const { onTick, minutes, wrapper } = mountAutoRefresh()
    minutes.value = 1
    await nextTick()
    wrapper.unmount()
    vi.advanceTimersByTime(5 * 60_000)
    expect(onTick).not.toHaveBeenCalled()
  })
})
