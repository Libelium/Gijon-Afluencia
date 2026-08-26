<script setup lang="ts">
import { computed } from 'vue'
import { LCircleMarker, LMap, LPolygon, LTileLayer, LTooltip } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import StateBlock from '@/components/StateBlock.vue'
import { t } from '@/i18n'
import { env, envNumber } from '@/lib/env'
import { formatMeasure } from '@/lib/format'
import { useChartTheme } from '../../../charts'
import { MUTED, occupancyColor } from '../../../palette'

export interface ZoneMarker {
  id: number
  name: string
  /** Ocupacion actual en personas, o null. */
  value: number | null
  /** Proporcion 0..n, o null si no hay aforo. */
  ratio: number | null
  latLng: [number, number]
  polygon: [number, number][] | null
  selected: boolean
}

const props = withDefaults(
  defineProps<{ markers: ZoneMarker[]; loading?: boolean; error?: string | null; height?: number }>(),
  { height: 340 },
)

defineEmits<{ select: [id: number]; retry: [] }>()

const { isDark } = useChartTheme()

const tiles = env('VITE_MAP_TILES_URL')
const attribution = env('VITE_MAP_TILES_ATTRIBUTION')

function colorOf(marker: ZoneMarker): string {
  if (marker.ratio === null) return isDark.value ? MUTED.dark : MUTED.light
  return occupancyColor(marker.ratio, isDark.value)
}

const center = computed<[number, number]>(() => {
  if (!props.markers.length) {
    const raw = env('VITE_MAP_DEFAULT_CENTER')
    const [lat, lon] = raw.split(',').map(Number)
    return Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : [0, 0]
  }
  const sum = props.markers.reduce(
    (acc, m) => [acc[0] + m.latLng[0], acc[1] + m.latLng[1]] as [number, number],
    [0, 0] as [number, number],
  )
  return [sum[0] / props.markers.length, sum[1] / props.markers.length]
})

const zoom = computed(() =>
  props.markers.length ? (props.markers.length > 1 ? 14 : 16) : envNumber('VITE_MAP_DEFAULT_ZOOM', 13),
)

function markerLabel(marker: ZoneMarker): string {
  const count = formatMeasure(marker.value, t('dashboards.lidar.people'))
  if (marker.ratio === null) return count
  return `${count} · ${formatMeasure(marker.ratio * 100, '%')}`
}
</script>

<template>
  <div
    class="rounded-lg overflow-hidden"
    :style="{ height: `${height}px` }"
    role="img"
    :aria-label="t('dashboards.lidar.heatmap.mapLabel')"
  >
    <StateBlock
      :loading="loading"
      :error="error"
      :empty="!markers.length"
      :empty-text="t('dashboards.lidar.heatmap.noGeo')"
      :empty-hint="t('dashboards.lidar.heatmap.noGeoHint')"
      empty-icon="mdi-map-marker-off-outline"
      skeleton="card"
      @retry="$emit('retry')"
    >
      <LMap :zoom="zoom" :center="center" :scroll-wheel-zoom="false" :style="{ height: `${height}px` }">
        <LTileLayer :url="tiles" :attribution="attribution" />
        <template v-for="marker in markers" :key="marker.id">
          <LPolygon
            v-if="marker.polygon"
            :lat-lngs="marker.polygon"
            :fill-color="colorOf(marker)"
            :fill-opacity="0.45"
            :color="colorOf(marker)"
            :weight="marker.selected ? 3 : 1.5"
            @click="$emit('select', marker.id)"
          />
          <LCircleMarker
            :lat-lng="marker.latLng"
            :radius="marker.selected ? 11 : 8"
            :fill-color="colorOf(marker)"
            :fill-opacity="0.95"
            color="#FFFFFF"
            :weight="2"
            @click="$emit('select', marker.id)"
          >
            <LTooltip>
              <div>{{ marker.name }}</div>
              <div class="text-caption">{{ markerLabel(marker) }}</div>
            </LTooltip>
          </LCircleMarker>
        </template>
      </LMap>
    </StateBlock>
  </div>
</template>
