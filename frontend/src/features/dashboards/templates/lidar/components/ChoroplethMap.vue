<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useId, watch } from 'vue'
import { useTheme } from 'vuetify'
import { LCircleMarker, LMap, LPolygon, LTileLayer, LTooltip } from '@vue-leaflet/vue-leaflet'
import type { LatLngBoundsExpression, Map as LeafletMap } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import DataTableAlternative from '@/components/DataTableAlternative.vue'
import { t } from '@/i18n'
import { formatMeasure, formatNumber } from '@/lib/format'
import { MAX_ZOOM, defaultCenter, defaultZoom, tilesForTheme } from '@/lib/mapConfig'
import { rowsTable } from '../../../charts/a11y'
import { AFORO_SCALE, INK, MUTED, aforoColor, darken } from '../../../palette'
import type { DeviceKind, ZoneDevice, ZoneState } from '../choropleth'

const props = withDefaults(
  defineProps<{ zones: ZoneState[]; devices?: ZoneDevice[]; selectedId?: number | null }>(),
  { devices: () => [], selectedId: null },
)

const emit = defineEmits<{ select: [id: number] }>()

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)
const tiles = computed(() => tilesForTheme(isDark.value))
const highlight = computed(() => theme.global.current.value.colors.primary)
const listId = useId()

const painted = computed(() => props.zones.filter((zone) => zone.polygon))

/** Cuanto se oscurece el borde: lo bastante para separar zonas vecinas del mismo tramo. */
const BORDER_DARKEN = 0.4

function colorOf(zone: ZoneState): string {
  if (zone.ratio === null) return isDark.value ? MUTED.dark : MUTED.light
  return aforoColor(zone.ratio)
}

function labelOf(zone: ZoneState): string {
  const people = formatMeasure(zone.value, t('dashboards.lidar.people'))
  return zone.ratio === null ? people : `${people} · ${formatMeasure(zone.ratio * 100, '%')}`
}

const legend = computed(() => [
  ...AFORO_SCALE.map((color, index) => ({
    color,
    label:
      index === AFORO_SCALE.length - 1
        ? t('dashboards.lidar.choropleth.levelFrom', { from: index * 20 })
        : t('dashboards.lidar.choropleth.level', { from: index * 20, to: (index + 1) * 20 }),
  })),
  { color: isDark.value ? MUTED.dark : MUTED.light, label: t('dashboards.lidar.choropleth.noCapacity') },
])

/**
 * Los dispositivos se distinguen por la forma de pintarlos, no por el color, que es del aforo:
 * el LIDAR relleno de tinta y el sensor WiFi/BLE hueco, los dos con borde para verse sobre cualquier
 * tramo.
 */
const DEVICE_STYLE: Record<DeviceKind, { radius: number; fill: string; stroke: string }> = {
  lidar: { radius: 7, fill: INK.light, stroke: '#FFFFFF' },
  smartspot: { radius: 6, fill: '#FFFFFF', stroke: INK.light },
}

const deviceLegend = computed(() =>
  (['lidar', 'smartspot'] as const)
    .filter((kind) => props.devices.some((device) => device.kind === kind))
    .map((kind) => ({ kind, label: t(`dashboards.lidar.choropleth.${kind}`), ...DEVICE_STYLE[kind] })),
)

const devicesTable = computed(() =>
  rowsTable(
    [
      t('dashboards.lidar.choropleth.zoneColumn'),
      t('dashboards.lidar.choropleth.kindColumn'),
      t('dashboards.lidar.choropleth.deviceColumn'),
      t('dashboards.lidar.choropleth.coordinatesColumn'),
    ],
    props.devices.map((device) => [
      device.zoneName,
      t(`dashboards.lidar.choropleth.${device.kind}`),
      device.serial,
      `${formatNumber(device.lat, 5)}, ${formatNumber(device.lon, 5)}`,
    ]),
  ),
)

const SHOW_DEVICES_KEY = 'choropleth.showDevices'

function readShowDevices(): boolean {
  try {
    return localStorage.getItem(SHOW_DEVICES_KEY) !== 'false'
  } catch {
    return true
  }
}

/** Se pueden ocultar para ver solo las zonas. Se recuerda en este navegador. */
const showDevices = ref(readShowDevices())

watch(showDevices, (value) => {
  try {
    localStorage.setItem(SHOW_DEVICES_KEY, String(value))
  } catch {
    // Sin almacenamiento (ventana privada) solo se pierde la preferencia al recargar.
  }
})

/**
 * Zoom suave: medio nivel por pulsacion de los botones, y la rueda pide el doble de giro por nivel
 * que por defecto. El zoom admite cuartos de nivel, asi que el encuadre se ajusta mejor a las zonas.
 * El doble clic no acerca: sobre una zona, la encuadra (`frameZone`).
 */
const ZOOM_OPTIONS = { zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 120, doubleClickZoom: false }

/** Doble clic en una zona: la encuadra entera, lo mas cerca que quepa. */
function frameZone(zone: ZoneState) {
  if (zone.polygon) map.value?.fitBounds(zone.polygon, { padding: [32, 32], maxZoom: MAX_ZOOM })
}

/**
 * Elegir una zona en la lista la selecciona y la encuadra, y trae el mapa a la vista si se habia
 * quedado fuera al bajar hasta la lista. Es tambien el equivalente por teclado del doble clic.
 */
function chooseFromList(zone: ZoneState) {
  emit('select', zone.id)
  if (!zone.polygon) return
  frameZone(zone)
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  frame.value?.scrollIntoView?.({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' })
}

const map = shallowRef<LeafletMap | null>(null)

/** Encuadra todas las zonas pintadas. Solo cuando cambia cuales son, no a cada hora. */
function fit() {
  const instance = map.value
  if (!instance || !painted.value.length) return
  const bounds = painted.value.flatMap((zone) => zone.polygon ?? []) as LatLngBoundsExpression
  instance.fitBounds(bounds, { padding: [24, 24], maxZoom: 18 })
}

watch(() => painted.value.map((zone) => zone.id).join(','), fit)

/**
 * El mapa es apaisado y no pasa del 60 % de la ventana: al cambiar de tamano, Leaflet tiene que
 * enterarse y se vuelven a encuadrar todas las zonas para que se vean enteras.
 */
const frame = ref<HTMLElement | null>(null)
let observer: ResizeObserver | undefined
let resizeTimer: ReturnType<typeof setTimeout> | undefined
/** Pixeles que tiene que cambiar el mapa para volver a encuadrar las zonas. */
const RESIZE_THRESHOLD = 40
let lastSize = { width: 0, height: 0 }

onMounted(() => {
  if (!frame.value || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    const { width, height } = entry.contentRect
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      map.value?.invalidateSize()
      // Solo un cambio de tamano real reencuadra. Elegir una zona mueve la pagina y la barra de
      // desplazamiento cambia el ancho unos pixeles: eso no puede deshacer el zoom que se tenia.
      if (Math.abs(width - lastSize.width) > RESIZE_THRESHOLD || Math.abs(height - lastSize.height) > RESIZE_THRESHOLD) {
        lastSize = { width, height }
        fit()
      }
    }, 160)
  })
  observer.observe(frame.value)
})

onBeforeUnmount(() => {
  clearTimeout(resizeTimer)
  observer?.disconnect()
})
</script>

<template>
  <div>
    <div
      ref="frame"
      class="choropleth rounded-lg overflow-hidden"
      :class="{ 'map-tiles--dark': tiles.darken }"
    >
      <!-- `group` y no `img`: dentro quedan el zoom y la atribucion, que deben seguir alcanzables. -->
      <LMap
        :center="defaultCenter()"
        :zoom="defaultZoom()"
        :max-zoom="MAX_ZOOM"
        :scroll-wheel-zoom="true"
        :double-click-zoom="false"
        :options="ZOOM_OPTIONS"
        :style="{ height: '100%' }"
        role="group"
        :aria-label="t('dashboards.lidar.choropleth.mapLabel')"
        @ready="(instance: LeafletMap) => { map = instance; fit() }"
      >
        <!-- La key recrea la capa al cambiar de tema: vue-leaflet solo aplica `options` al crearla. -->
        <LTileLayer :key="tiles.url" :url="tiles.url" :attribution="tiles.attribution" :options="tiles.options" />
        <LPolygon
          v-for="zone in painted"
          :key="zone.id"
          :lat-lngs="zone.polygon!"
          :fill-color="colorOf(zone)"
          :fill-opacity="0.65"
          :color="zone.id === selectedId ? highlight : darken(colorOf(zone), BORDER_DARKEN)"
          :weight="zone.id === selectedId ? 4 : 2.5"
          @click="$emit('select', zone.id)"
          @dblclick="frameZone(zone)"
        >
          <LTooltip>
            <div class="text-body-2 font-weight-medium">{{ zone.name }}</div>
            <div class="text-caption">{{ labelOf(zone) }}</div>
          </LTooltip>
        </LPolygon>
        <LCircleMarker
          v-for="device in showDevices ? devices : []"
          :key="device.key"
          :lat-lng="[device.lat, device.lon]"
          :radius="DEVICE_STYLE[device.kind].radius"
          :fill-color="DEVICE_STYLE[device.kind].fill"
          :fill-opacity="1"
          :color="DEVICE_STYLE[device.kind].stroke"
          :weight="2"
        >
          <LTooltip>
            <div class="text-body-2 font-weight-medium">{{ t(`dashboards.lidar.choropleth.${device.kind}`) }} · {{ device.serial }}</div>
            <div class="text-caption">{{ device.zoneName }}</div>
          </LTooltip>
        </LCircleMarker>
      </LMap>
    </div>

    <div class="d-flex flex-wrap align-center ga-4 mt-3">
      <span
        v-for="item in legend"
        :key="item.label"
        class="d-inline-flex align-center ga-2 text-caption text-medium-emphasis"
      >
        <span class="choropleth__swatch" :style="{ background: item.color }" />
        {{ item.label }}
      </span>
      <span
        v-for="item in showDevices ? deviceLegend : []"
        :key="item.kind"
        class="d-inline-flex align-center ga-2 text-caption text-medium-emphasis"
      >
        <span
          class="choropleth__device"
          :style="{ background: item.fill, borderColor: item.stroke, inlineSize: `${item.radius * 2}px`, blockSize: `${item.radius * 2}px` }"
        />
        {{ item.label }}
      </span>
      <VSpacer />
      <VSwitch
        v-if="devices.length"
        v-model="showDevices"
        :label="t('dashboards.lidar.choropleth.showDevices')"
        color="primary"
        density="compact"
        hide-details
        class="flex-grow-0"
      />
    </div>

    <DataTableAlternative
      v-if="devices.length"
      :title="t('dashboards.lidar.choropleth.devicesTable')"
      :table="devicesTable"
    />

    <!-- Equivalente por teclado y alternativa textual del mapa: los poligonos de Leaflet son
         `<path>` de SVG, sin foco ni teclado, y su color solo dice el tramo, no la cifra. -->
    <div v-if="zones.length" class="mt-4">
      <div :id="listId" class="text-caption text-medium-emphasis mb-2">
        {{ t('dashboards.lidar.choropleth.zoneListHint') }}
      </div>
      <div class="d-flex flex-wrap ga-2" role="group" :aria-labelledby="listId">
        <VBtn
          v-for="zone in zones"
          :key="zone.id"
          size="small"
          :variant="zone.id === selectedId ? 'flat' : 'tonal'"
          :color="zone.id === selectedId ? 'primary' : undefined"
          :aria-pressed="zone.id === selectedId"
          @click="chooseFromList(zone)"
        >
          <span class="choropleth__swatch choropleth__swatch--round me-2" :style="{ background: colorOf(zone) }" />
          {{ zone.name }}
          <span class="text-medium-emphasis ms-2">{{ labelOf(zone) }}</span>
          <span v-if="!zone.polygon" class="text-medium-emphasis ms-1">
            · {{ t('dashboards.lidar.choropleth.notPainted') }}
          </span>
        </VBtn>
      </div>
    </div>
  </div>
</template>

<style scoped>
.choropleth__device {
  display: inline-block;
  border: 2px solid;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgb(var(--v-theme-outline));
  flex: 0 0 auto;
}

.choropleth {
  border: 1px solid rgb(var(--v-theme-outline));
  /* Apaisado y sin pasar del 60 % de la ventana: se ve entero con la barra de horas y la leyenda. */
  aspect-ratio: 16 / 9;
  max-block-size: 60vh;
  min-block-size: 360px;
  inline-size: 100%;
}

.choropleth__swatch {
  display: inline-block;
  inline-size: 12px;
  block-size: 12px;
  border-radius: 3px;
  flex: 0 0 auto;
}

.choropleth__swatch--round {
  inline-size: 10px;
  block-size: 10px;
  border-radius: 50%;
}

:deep(.leaflet-container) {
  background: rgb(var(--v-theme-surface-variant));
  font-family: inherit;
}
</style>
