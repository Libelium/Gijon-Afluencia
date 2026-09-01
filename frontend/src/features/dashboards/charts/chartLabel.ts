import { computed, inject, provide, toValue, type ComputedRef, type InjectionKey, type MaybeRefOrGetter } from 'vue'

/**
 * Nombre accesible de una grafica, heredado de la tarjeta que la contiene.
 *
 * El problema que resuelve: el titulo de un grafico lo pinta la TARJETA, no el grafico, asi que
 * el lienzo no sabe como se llama lo que esta dibujando. Y ese titulo es justo lo que hace falta
 * para dos cosas: el nombre accesible del `<canvas>` y el encabezado de la tabla equivalente
 * (WCAG 1.1.1, hallazgo GDTIS-PT01-ACC-002).
 *
 * Se resuelve por inyeccion y no repitiendo el titulo en cada llamada porque hay una veintena de
 * usos repartidos por las plantillas: con `provide` en las tarjetas, cualquier grafico nuevo
 * hereda su nombre sin que nadie tenga que acordarse.
 */
const CHART_LABEL: InjectionKey<ComputedRef<string>> = Symbol('chart-label')

/** Lo llama la tarjeta que pinta el titulo visible. */
export function provideChartLabel(label: MaybeRefOrGetter<string>): void {
  provide(
    CHART_LABEL,
    computed(() => toValue(label)),
  )
}

/**
 * Nombre a usar, por orden de preferencia: el que pasa quien monta el grafico, el de la tarjeta
 * que lo contiene, y como ultimo recurso el generico del tipo de grafico.
 */
export function useChartLabel(
  explicit: MaybeRefOrGetter<string | undefined>,
  fallback: MaybeRefOrGetter<string>,
): ComputedRef<string> {
  const inherited = inject(CHART_LABEL, null)
  return computed(() => toValue(explicit) || inherited?.value || toValue(fallback))
}
