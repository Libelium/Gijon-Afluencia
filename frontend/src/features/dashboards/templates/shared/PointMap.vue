<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useTheme } from 'vuetify'
import { LMap, LTileLayer, LCircleMarker, LPolyline, LTooltip } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import type { Map as LeafletMap, LatLngBoundsExpression } from 'leaflet'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { rowsTable } from '../../charts/a11y'
import { defaultCenter, defaultZoom, tilesForTheme } from '@/lib/mapConfig'
import { SURFACE } from '../../palette'

export interface MapPoint {
  key: string
  lat: number
  lon: number
  label: string
  /** Texto ya formateado del valor. Se muestra bajo la etiqueta en el globo. */
  text: string
  /** Color de relleno. Lo decide la plantilla con occupancyColor() o seriesColors(). */
  color: string
  /** Radio en pixeles. Entre 6 y 22. */
  radius: number
}

export interface MapLink {
  key: string
  from: [number, number]
  to: [number, number]
  label: string
  text: string
  /** Grosor en pixeles, entre 1 y 8. */
  weight: number
  color: string
}

const props = withDefaults(
  defineProps<{
    points: MapPoint[]
    links?: MapLink[]
    height?: number
    /** Leyenda de niveles bajo el mapa. */
    legend?: { color: string; label: string }[]
  }>(),
  { height: 360, links: () => [] },
)

// Cartografia y encuadre inicial salen de `@/lib/mapConfig`, igual que en la vista de mapa.
// La atribucion es obligacion de la licencia de las teselas: siempre visible.

const center = defaultCenter()
const zoom = defaultZoom()

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)
const stroke = computed(() => (isDark.value ? SURFACE.dark : SURFACE.light))
const tiles = computed(() => tilesForTheme(isDark.value))

const canvas = ref<HTMLElement | null>(null)
const map = shallowRef<LeafletMap | null>(null)

function fit() {
  const instance = map.value
  if (!instance || props.points.length === 0) return
  if (props.points.length === 1) {
    const point = props.points[0]
    instance.setView([point.lat, point.lon], 16)
    return
  }
  const bounds = props.points.map((p) => [p.lat, p.lon]) as LatLngBoundsExpression
  instance.fitBounds(bounds, { padding: [24, 24], maxZoom: 17 })
}

function onReady(instance: LeafletMap) {
  map.value = instance
  fit()
}

watch(() => props.points, fit, { deep: false })

/**
 * Leaflet cachea el tamaño de su contenedor: hay que avisarle cuando cambia (al plegar el
 * menu lateral, al redimensionar la ventana), igual que en MapView.vue.
 */
let resizeTimer: ReturnType<typeof setTimeout> | undefined
let observer: ResizeObserver | undefined

function onCanvasResize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => map.value?.invalidateSize(), 160)
}

onMounted(() => {
  const el = canvas.value
  if (!el || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(onCanvasResize)
  observer.observe(el)
})

onBeforeUnmount(() => {
  if (resizeTimer) clearTimeout(resizeTimer)
  observer?.disconnect()
})

/**
 * Alternativa textual del mapa (WCAG 1.1.1, hallazgo GDTIS-PT01-ACC-001).
 *
 * Los circulos y las lineas son `<path>` de SVG dentro del lienzo de Leaflet: su valor solo se
 * lee acercando el raton para que salga el globo. La tabla ofrece el mismo dato —rotulo, valor
 * y posicion— sin depender del puntero ni de percibir el tamano y el color.
 */
const pointsTable = computed(() =>
  rowsTable(
    [
      t('templates.common.pointColumn'),
      t('templates.common.value'),
      t('templates.common.coordinatesColumn'),
    ],
    props.points.map((point) => [
      point.label,
      point.text,
      `${formatNumber(point.lat, 5)}, ${formatNumber(point.lon, 5)}`,
    ]),
  ),
)

const linksTable = computed(() =>
  rowsTable(
    [t('templates.common.linkColumn'), t('templates.common.value')],
    props.links.map((link) => [link.label, link.text]),
  ),
)
</script>

<template>
  <div>
    <!-- Leaflet necesita una altura explicita en su contenedor: sin ella el mapa no se dibuja. -->
    <div
      ref="canvas"
      class="point-map rounded-lg overflow-hidden"
      :style="{ height: `${height}px` }"
    >
      <!-- `group` y no `img`: dentro del mapa hay controles que deben seguir siendo
           alcanzables (zoom, enlace de atribucion). La alternativa textual es la tabla que
           va justo debajo. -->
      <LMap
        :center="center"
        :zoom="zoom"
        :min-zoom="3"
        :max-zoom="19"
        :scroll-wheel-zoom="false"
        role="group"
        :aria-label="t('templates.common.mapLabel')"
        @ready="onReady"
      >
        <LTileLayer :url="tiles.url" :attribution="tiles.attribution" :options="{ maxZoom: 19, detectRetina: true }" />

        <!-- Las lineas van antes que los circulos para que estos queden encima. -->
        <LPolyline
          v-for="link in links"
          :key="link.key"
          :lat-lngs="[link.from, link.to]"
          :color="link.color"
          :weight="link.weight"
          :opacity="0.7"
        >
          <LTooltip>
            <div class="text-body-2 font-weight-medium">{{ link.label }}</div>
            <div class="text-caption">{{ link.text }}</div>
          </LTooltip>
        </LPolyline>

        <LCircleMarker
          v-for="point in points"
          :key="point.key"
          :lat-lng="[point.lat, point.lon]"
          :radius="point.radius"
          :color="stroke"
          :weight="2"
          :fill-color="point.color"
          :fill-opacity="0.9"
        >
          <LTooltip>
            <div class="text-body-2 font-weight-medium">{{ point.label }}</div>
            <div class="text-caption">{{ point.text }}</div>
          </LTooltip>
        </LCircleMarker>
      </LMap>
    </div>

    <DataTableAlternative
      :title="t('templates.common.mapLabel')"
      :table="pointsTable"
      :label="t('templates.common.mapTable')"
    />

    <DataTableAlternative
      v-if="links.length"
      :title="t('templates.common.linkColumn')"
      :table="linksTable"
    />

    <div v-if="legend?.length" class="d-flex flex-wrap align-center ga-4 mt-3">
      <span
        v-for="item in legend"
        :key="item.label"
        class="d-inline-flex align-center ga-2 text-caption text-medium-emphasis"
      >
        <span class="point-map__swatch" :style="{ background: item.color }" />
        {{ item.label }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.point-map {
  border: 1px solid rgb(var(--v-theme-outline));
}

.point-map__swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex: 0 0 auto;
}

:deep(.leaflet-container) {
  background: rgb(var(--v-theme-surface-variant));
  font-family: inherit;
}

:deep(.leaflet-tooltip) {
  padding: 6px 10px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border: 1px solid rgb(var(--v-theme-outline));
  box-shadow: 0 4px 14px rgb(0 0 0 / 16%);
}

:deep(.leaflet-container .leaflet-control-attribution) {
  padding: 3px 10px;
  border-start-start-radius: 10px;
  background: rgba(var(--v-theme-surface), 0.92);
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  box-shadow: none;
}

:deep(.leaflet-container .leaflet-control-attribution a) {
  color: rgb(var(--v-theme-primary));
}


</style>
