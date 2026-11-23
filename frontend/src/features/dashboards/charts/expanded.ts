import { computed, inject, provide, ref, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import { chartStyle } from './chartOptions'

/**
 * Una tarjeta ampliada a pantalla completa avisa a las graficas que contiene, que pasan a ocupar
 * casi todo el alto de la ventana en lugar del suyo.
 */
const EXPANDED_KEY: InjectionKey<Ref<boolean>> = Symbol('chartExpanded')

/** Alto que dejan libre la cabecera de la tarjeta, sus controles y el margen del marco. */
export const EXPANDED_CHROME = 240

export function provideExpanded(expanded: Ref<boolean>): void {
  provide(EXPANDED_KEY, expanded)
}

export function useExpanded(): Ref<boolean> {
  return inject(EXPANDED_KEY, ref(false))
}

const viewportHeight = ref(typeof window === 'undefined' ? 0 : window.innerHeight)
let listening = false

function watchViewport() {
  if (listening || typeof window === 'undefined') return
  listening = true
  window.addEventListener('resize', () => (viewportHeight.value = window.innerHeight), { passive: true })
}

/** Alto de una grafica ampliada: el de la ventana menos el marco, y nunca menos que el suyo. */
export function expandedHeight(height: number | string, viewport: number): number | string {
  const room = viewport - EXPANDED_CHROME
  if (typeof height !== 'number') return room > 0 ? `max(${height}, ${room}px)` : height
  return Math.max(height, room)
}

/** Alto efectivo de una grafica: el que pide, o el de la pantalla si su tarjeta esta ampliada. */
export function useChartHeight(height: () => number | string): ComputedRef<number | string> {
  const expanded = useExpanded()
  watchViewport()
  return computed(() => (expanded.value ? expandedHeight(height(), viewportHeight.value) : height()))
}

export function useChartStyle(height: () => number | string) {
  const effective = useChartHeight(height)
  return computed(() => chartStyle(effective.value))
}
