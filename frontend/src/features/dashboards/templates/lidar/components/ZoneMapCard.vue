<script setup lang="ts">
import { computed, useId } from 'vue'
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

/** Radio en pixeles del circulo de zona. 12 px de radio son 24 px de diametro (WCAG 2.5.8). */
const MARKER_RADIUS = 12
const MARKER_RADIUS_SELECTED = 14

const listId = useId()

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
  <div>
    <!-- El rol y el nombre van en el mapa, no en este envoltorio: el envoltorio contiene
         tambien el bloque de estado con su boton «Reintentar», y `role` sobre el conjunto
         convertiria ese boton en parte de una imagen. `group` —y no `img`— porque dentro hay
         controles que deben seguir siendo alcanzables: el zoom y el enlace de atribucion. -->
    <div class="rounded-lg overflow-hidden" :style="{ height: `${height}px` }">
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
        <LMap
          :zoom="zoom"
          :center="center"
          :scroll-wheel-zoom="false"
          :style="{ height: `${height}px` }"
          role="group"
          :aria-label="t('dashboards.lidar.heatmap.mapLabel')"
        >
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
            <!-- Radio 12 px = 24 px de diametro, que es el minimo de WCAG 2.5.8 para un
                 objetivo tactil. Con los 8 px de antes el circulo medía 16 px y fallaba el
                 criterio (hallazgo GDTIS-PT01-ACC-010). -->
            <LCircleMarker
              :lat-lng="marker.latLng"
              :radius="marker.selected ? MARKER_RADIUS_SELECTED : MARKER_RADIUS"
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

    <!-- Equivalente por teclado y alternativa textual del mapa (WCAG 2.1.1 y 1.1.1, hallazgo
         GDTIS-PT01-ACC-001). Los circulos y los poligonos de Leaflet son `<path>` de SVG: no
         reciben foco ni eventos de teclado, asi que el `@click` del marcador NO tiene
         equivalente posible dentro del mapa. Esta lista es ese equivalente, y ademas pone en
         texto lo unico que el mapa dice con color: la ocupacion de cada zona. -->
    <div v-if="markers.length" class="mt-3">
      <div :id="listId" class="text-caption text-medium-emphasis mb-2">
        {{ t('dashboards.lidar.heatmap.zoneListHint') }}
      </div>
      <div class="d-flex flex-wrap ga-2" role="group" :aria-labelledby="listId">
        <VBtn
          v-for="marker in markers"
          :key="marker.id"
          size="small"
          :variant="marker.selected ? 'flat' : 'tonal'"
          :color="marker.selected ? 'primary' : undefined"
          :aria-pressed="marker.selected"
          @click="$emit('select', marker.id)"
        >
          <span class="zone-swatch me-2" :style="{ background: colorOf(marker) }" />
          {{ marker.name }}
          <span class="text-medium-emphasis ms-2">{{ markerLabel(marker) }}</span>
        </VBtn>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* El color de la muestra repite el del marcador. Nunca es el unico portador del dato: al lado
   va siempre la cifra de ocupacion. */
.zone-swatch {
  display: inline-block;
  inline-size: 10px;
  block-size: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
}
</style>
