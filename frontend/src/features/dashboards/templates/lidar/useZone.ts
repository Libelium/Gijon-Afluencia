import { computed, onMounted, ref, watch, type ComputedRef, type Ref } from 'vue'
import { errorMessage } from '@/api/http'
import { getEntityMeasures } from '@/features/entities/api/entities'
import { useSessionStore } from '@/stores/session'
import type { Dashboard, Entity, Measure } from '@/types'
import { DEFAULT_RANGE, resolveRange, type DateRange, type RangePresetId } from '../../lib/range'
import { describeZone, fetchTemplateEntities, refOf, zoneEntities, type ZoneProfile } from './data'

export interface UseZoneProps {
  dashboard: Dashboard
  range?: DateRange
  timeZone?: string
  reloadKey?: number
}

export interface UseZone {
  zones: Ref<Entity[]>
  zoneId: Ref<number | null>
  zone: ComputedRef<Entity | null>
  measures: Ref<Measure[]>
  profile: ComputedRef<ZoneProfile | null>
  usedFallbackEntities: Ref<boolean>
  preset: Ref<RangePresetId>
  range: ComputedRef<DateRange>
  ownRange: ComputedRef<boolean>
  timeZone: ComputedRef<string>
  loading: Ref<boolean>
  error: Ref<string | null>
  reload: () => Promise<void>
}

/** Composable compartido por las tres vistas de zona LIDAR: entidades, medidas, rango y recarga. */
export function useZone(props: UseZoneProps): UseZone {
  const session = useSessionStore()

  const zones = ref<Entity[]>([])
  const zoneId = ref<number | null>(null)
  const measures = ref<Measure[]>([])
  const usedFallbackEntities = ref(false)
  const preset = ref<RangePresetId>(DEFAULT_RANGE)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const zone = computed<Entity | null>(() => zones.value.find((z) => z.id === zoneId.value) ?? null)
  const profile = computed<ZoneProfile | null>(() =>
    measures.value.length ? describeZone(measures.value) : null,
  )

  const timeZone = computed(() => props.timeZone || props.dashboard.timezone || session.timeZone)
  const ownRange = computed(() => !props.range)
  const range = computed<DateRange>(() => props.range ?? resolveRange(preset.value, timeZone.value))

  async function loadEntities() {
    const all = await fetchTemplateEntities(props.dashboard.id)
    const { zones: loaded, usedFallback } = zoneEntities(all)
    zones.value = loaded
    usedFallbackEntities.value = usedFallback
    if (!loaded.some((e) => e.id === zoneId.value)) zoneId.value = loaded[0]?.id ?? null
  }

  async function loadMeasures() {
    measures.value = zone.value ? await getEntityMeasures(refOf(zone.value)) : []
  }

  async function reload() {
    loading.value = true
    error.value = null
    try {
      await loadEntities()
      await loadMeasures()
    } catch (e) {
      error.value = errorMessage(e)
      measures.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => zoneId.value,
    () => void loadMeasures(),
  )
  watch(
    () => props.reloadKey,
    () => void reload(),
  )
  onMounted(() => void reload())

  return {
    zones,
    zoneId,
    zone,
    measures,
    profile,
    usedFallbackEntities,
    preset,
    range,
    ownRange,
    timeZone,
    loading,
    error,
    reload,
  }
}
