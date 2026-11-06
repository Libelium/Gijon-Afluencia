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
import { MAX_ZOOM, defaultCenter, defaultZoom, tilesForTheme } from '@/lib/mapConfig'
import { SURFACE } from '../../palette'
import { curvedPath, type LatLng } from './curves'

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
  /**
   * Un recorrido con sentido: se dibuja en arco, apartado a la derecha de la marcha, para que la ida
   * y la vuelta entre dos puntos no se pisen, y con un trazo discontinuo que avanza hacia el
   * destino. Sin el, una recta continua.
   */
  curved?: boolean
}

const props = withDefaults(
  defineProps<{
    points: MapPoint[]
    links?: MapLink[]
    height?: number
    /** Leyenda de niveles bajo el mapa. */
    legend?: { color: string; label: string }[]
    /** Punto resaltado, por su clave. */
    selected?: string | null
  }>(),
  { height: 360, links: () => [], selected: null },
)

/** Al pulsar un punto. Su clave; la plantilla decide que hace con ella. */
const emit = defineEmits<{ select: [key: string] }>()

// Cartografia y encuadre inicial salen de `@/lib/mapConfig`, igual que en la vista de mapa.
// La atribucion es obligacion de la licencia de las teselas: siempre visible.

const center = defaultCenter()
const zoom = defaultZoom()

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)
const stroke = computed(() => (isDark.value ? SURFACE.dark : SURFACE.light))
const highlight = computed(() => theme.global.current.value.colors.primary)

/** El trazo de cada recorrido: la recta, o el arco. */
const drawnLinks = computed(() =>
  props.links.map((link) => ({
    link,
    path: link.curved ? curvedPath(link.from, link.to) : ([link.from, link.to] as LatLng[]),
  })),
)

/** Trazo y hueco de un recorrido en arco. La animacion desplaza el trazo justo su suma. */
const FLOW_DASH = '8 10'

const hasFlow = computed(() => props.links.some((link) => link.curved))

/**
 * El movimiento dice hacia donde va la gente, pero no puede ser obligatorio (WCAG 2.2.2): se puede
 * parar, y empieza parado si el sistema pide reducir el movimiento.
 */
const flowing = ref(
  typeof window === 'undefined' || !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
)
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
      :class="{ 'map-tiles--dark': tiles.darken, 'point-map--flowing': hasFlow && flowing }"
      :style="{ height: `${height}px` }"
    >
      <!-- `group` y no `img`: dentro del mapa hay controles que deben seguir siendo
           alcanzables (zoom, enlace de atribucion). La alternativa textual es la tabla que
           va justo debajo. -->
      <LMap
        :center="center"
        :zoom="zoom"
        :min-zoom="3"
        :max-zoom="MAX_ZOOM"
        :scroll-wheel-zoom="false"
        role="group"
        :aria-label="t('templates.common.mapLabel')"
        @ready="onReady"
      >
        <!-- La key recrea la capa al cambiar de tema: vue-leaflet solo aplica `options` al crearla. -->
        <LTileLayer :key="tiles.url" :url="tiles.url" :attribution="tiles.attribution" :options="tiles.options" />

        <!-- Las lineas van antes que los circulos para que estos queden encima. -->
        <LPolyline
          v-for="{ link, path } in drawnLinks"
          :key="link.key"
          :lat-lngs="path"
          :color="link.color"
          :weight="link.weight"
          :opacity="0.85"
          :dash-array="link.curved ? FLOW_DASH : undefined"
          :line-cap="link.curved ? 'round' : undefined"
          :class-name="link.curved ? 'point-map__flow' : undefined"
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
          :color="point.key === selected ? highlight : stroke"
          :weight="point.key === selected ? 4 : 2"
          :fill-color="point.color"
          :fill-opacity="0.9"
          @click="emit('select', point.key)"
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

    <div v-if="legend?.length || hasFlow" class="d-flex flex-wrap align-center ga-4 mt-3">
      <span
        v-for="item in legend"
        :key="item.label"
        class="d-inline-flex align-center ga-2 text-caption text-medium-emphasis"
      >
        <span class="point-map__swatch" :style="{ background: item.color }" />
        {{ item.label }}
      </span>
      <VSpacer />
      <VBtn
        v-if="hasFlow"
        variant="text"
        size="small"
        :prepend-icon="flowing ? 'mdi-pause' : 'mdi-play'"
        @click="flowing = !flowing"
      >
        {{ flowing ? t('templates.common.flowPause') : t('templates.common.flowResume') }}
      </VBtn>
    </div>
  </div>
</template>

<style scoped>
.point-map {
  border: 1px solid rgb(var(--v-theme-outline));
}

/* El trazo avanza del origen al destino: desplazarlo su periodo entero hace el bucle continuo. */
.point-map--flowing :deep(.point-map__flow) {
  animation: point-map-flow 1.2s linear infinite;
}

@keyframes point-map-flow {
  to {
    stroke-dashoffset: -18;
  }
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
