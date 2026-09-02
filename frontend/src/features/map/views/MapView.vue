<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { LMap, LMarker, LPopup, LTileLayer } from '@vue-leaflet/vue-leaflet'
import type { Map as LeafletMap } from 'leaflet'
import { errorMessage } from '@/api/http'
import { useDebouncedResize } from '@/composables/useDebouncedResize'
import { t } from '@/i18n'
import { formatNumber, urnTail } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import type { Bounds, Entity } from '@/types'
import { listDatamodels, listEntitiesInBounds, sampleEntities } from '../api/map'
import EntityClusterGroup from '../components/EntityClusterGroup.vue'
import EntityPopupCard from '../components/EntityPopupCard.vue'
import MapControlPanel from '../components/MapControlPanel.vue'
import { createEntityIcon } from '../lib/cluster'
import { boundsOf, placeEntities, type PlacedEntity } from '../lib/geometry'
import { defaultCenter, defaultZoom, tilesAttribution as tilesAttributionOf, tilesUrl as tilesUrlOf } from '@/lib/mapConfig'

/** Tope de marcadores por vista: el mapa pide solo el area visible, nunca el inventario. */
const MAX_MARKERS = 300
const MOVE_DEBOUNCE_MS = 500
const FILTER_DEBOUNCE_MS = 400
const RESIZE_DEBOUNCE_MS = 160
// La cartografia se lee de `@/lib/mapConfig`, que consulta la configuracion inyectada por el
// contenedor antes de la incrustada al compilar: asi se puede cambiar el proveedor de teselas
// en el despliegue sin reconstruir la imagen. La atribucion es obligatoria por su licencia.
const tilesUrl = tilesUrlOf()
const tilesAttribution = tilesAttributionOf()
const center = defaultCenter()
const zoom = defaultZoom()

const router = useRouter()
const theme = useTheme()
const markerIcon = createEntityIcon()

const canvas = ref<HTMLElement | null>(null)
const map = shallowRef<LeafletMap | null>(null)
const mapReady = ref(false)
const placed = shallowRef<PlacedEntity[]>([])
const withoutLocation = ref(0)
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const search = ref('')
const datamodel = ref<string | null>(null)
const datamodels = ref<string[]>([])
const datamodelsLoading = ref(false)
const locating = ref(false)
const locateFailed = ref(false)

const dark = computed(() => theme.global.current.value.dark)
const filtered = computed(() => Boolean(search.value.trim()) || Boolean(datamodel.value))
const empty = computed(() => !loading.value && !error.value && placed.value.length === 0)
const showState = computed(() => Boolean(error.value) || empty.value)
const emptyText = computed(() => (filtered.value ? t('map.emptyFiltered') : t('map.empty')))
// El aviso solo intercepta el raton cuando ofrece algo que pulsar. Al quedarse vacio siempre
// ofrece llevar el mapa a donde hay datos, asi que en ese estado tambien tiene que ser pulsable.
const stateInteractive = computed(() => Boolean(error.value) || empty.value)

let moveTimer: ReturnType<typeof setTimeout> | undefined
let pending: AbortController | undefined
// Solo la PRIMERA carga puede recolocar la vista. Si mas adelante el usuario arrastra el mapa a
// una zona vacia lo ha hecho a proposito, y moverle el encuadre por debajo seria peor que el vacio.
let firstLoadDone = false

function visibleBounds(): Bounds | null {
  const instance = map.value
  if (!instance) return null
  const box = instance.getBounds()
  return {
    south: Math.max(-90, box.getSouth()),
    west: Math.max(-180, box.getWest()),
    north: Math.min(90, box.getNorth()),
    east: Math.min(180, box.getEast()),
  }
}

async function load() {
  const bounds = visibleBounds()
  if (!bounds) return

  pending?.abort()
  const current = new AbortController()
  pending = current
  loading.value = true
  error.value = null

  try {
    const page = await listEntitiesInBounds(bounds, {
      search: search.value.trim() || undefined,
      types: datamodel.value || undefined,
      paginationSize: MAX_MARKERS,
      signal: current.signal,
    })
    const result = placeEntities(page.rows)
    placed.value = result.placed
    withoutLocation.value = result.withoutLocation
    total.value = page.count

    const wasFirst = !firstLoadDone
    firstLoadDone = true
    // El centro configurado en el despliegue no es donde estan los datos: se busca donde si.
    if (wasFirst && page.count === 0 && !filtered.value) void locateData()
  } catch (e) {
    // Una peticion cancelada es una vista anterior quedandose atras, no un fallo que mostrar.
    if (current.signal.aborted) return
    error.value = errorMessage(e)
    placed.value = []
    withoutLocation.value = 0
    total.value = 0
  } finally {
    if (pending === current) loading.value = false
  }
}

/**
 * Lleva el mapa a donde estan las entidades. Es una ayuda, no una funcion critica: si falla, el
 * mapa sigue siendo utilizable y el aviso de zona vacia sigue en pantalla.
 */
async function locateData() {
  if (locating.value) return
  locating.value = true
  locateFailed.value = false
  try {
    const rows = await sampleEntities({
      search: search.value.trim() || undefined,
      types: datamodel.value || undefined,
      paginationSize: MAX_MARKERS,
    })
    const box = boundsOf(placeEntities(rows).placed)
    const instance = map.value
    if (!box || !instance) {
      locateFailed.value = true
      return
    }
    // `fitBounds` dispara `moveend`, y de ahi sale la carga del area nueva: no se pide aqui.
    instance.fitBounds(
      [
        [box.south, box.west],
        [box.north, box.east],
      ],
      { padding: [48, 48], maxZoom: 16 },
    )
  } catch {
    locateFailed.value = true
  } finally {
    locating.value = false
  }
}

function schedule(delay: number) {
  if (moveTimer) clearTimeout(moveTimer)
  moveTimer = setTimeout(() => void load(), delay)
}

const onMoveEnd = () => schedule(MOVE_DEBOUNCE_MS)

function onMapReady(instance: LeafletMap) {
  map.value = instance
  // El zoom baja a la esquina opuesta: arriba a la izquierda va el panel de control.
  instance.zoomControl?.setPosition('bottomright')
  instance.on('moveend', onMoveEnd)
  mapReady.value = true
  void load()
}

// Leaflet cachea el tamaño de su contenedor y hay que avisarle cuando cambia: al plegar el menu
// lateral, al girar el movil o al redimensionar la ventana. `useDebouncedResize` observa el lienzo
// y recalcula el tamaño (rebotado) solo cuando cambia de veras.
useDebouncedResize(canvas, () => map.value?.invalidateSize(), RESIZE_DEBOUNCE_MS)

async function loadDatamodels() {
  datamodelsLoading.value = true
  try {
    datamodels.value = await listDatamodels()
  } catch {
    // El filtro es accesorio: si el catalogo falla, el mapa sigue siendo utilizable.
    datamodels.value = []
  } finally {
    datamodelsLoading.value = false
  }
}

function openEntity(entity: Entity) {
  void router.push(`/entidades/${entity.id}`)
}

function clearFilters() {
  search.value = ''
  datamodel.value = null
}

/**
 * Alternativa textual y por teclado del mapa (WCAG 1.1.1 y 2.1.1, hallazgo GDTIS-PT01-ACC-001).
 *
 * Un mapa de marcadores no se puede recorrer con el teclado de forma util —Leaflet dibuja los
 * marcadores agrupados y el globo emergente se abre sobre el lienzo—, y para un lector de
 * pantalla el mapa es un `<canvas>` de teselas. La misma consulta que pinta los marcadores
 * alimenta esta tabla, asi que lo que se lista es EXACTAMENTE lo que se ve, se actualiza con el
 * encuadre y cada fila lleva su enlace al detalle: es la ruta equivalente completa.
 */
const tableHeaders = [
  { title: t('map.table.name'), key: 'name', sortable: false },
  { title: t('map.table.datamodel'), key: 'datamodel', sortable: false },
  { title: t('map.table.coordinates'), key: 'coordinates', sortable: false },
]

const tableRows = computed(() =>
  placed.value.map((item) => ({
    id: item.entity.id,
    name: item.entity.name || urnTail(item.entity.urn),
    datamodel: item.entity.datamodel || t('common.noValue'),
    coordinates: `${formatNumber(item.latLng[0], 5)}, ${formatNumber(item.latLng[1], 5)}`,
  })),
)

const tableToggleText = computed(() => {
  if (!placed.value.length) return t('map.table.toggleEmpty')
  if (placed.value.length === 1) return t('map.table.toggleOne')
  return t('map.table.toggle', { n: formatNumber(placed.value.length, 0) })
})

watch([search, datamodel], () => schedule(FILTER_DEBOUNCE_MS))

onBeforeUnmount(() => {
  if (moveTimer) clearTimeout(moveTimer)
  pending?.abort()
  map.value?.off('moveend', onMoveEnd)
})

void loadDatamodels()
</script>

<template>
  <div class="map-view d-flex flex-column">
    <PageHeader :title="t('map.title')" :subtitle="t('map.subtitle')" />

    <div
      ref="canvas"
      class="map-canvas flex-grow-1 position-relative overflow-hidden rounded-lg"
      :class="{ 'map-canvas--dark': dark }"
    >
      <!-- `keyboard` es el valor por defecto de Leaflet, pero se declara aqui a proposito:
           es la unica forma de que se vea, al leer esta plantilla, que el lienzo se desplaza
           con las flechas y se amplia con + y −. La alternativa completa es la tabla de abajo. -->
      <LMap
        :center="center"
        :zoom="zoom"
        :min-zoom="3"
        :max-zoom="19"
        :use-global-leaflet="true"
        :options="{ keyboard: true }"
        role="group"
        :aria-label="t('map.mapLabel')"
        @ready="onMapReady"
      >
        <LTileLayer
          :url="tilesUrl"
          :attribution="tilesAttribution"
          :options="{ maxZoom: 19, detectRetina: true }"
        />

        <EntityClusterGroup v-if="mapReady">
          <LMarker
            v-for="item in placed"
            :key="item.entity.id"
            :lat-lng="item.latLng"
            :icon="markerIcon"
            :options="{ title: item.entity.name || item.entity.urn, riseOnHover: true }"
          >
            <LPopup :options="{ minWidth: 236, maxWidth: 296, autoPanPadding: [24, 24] }">
              <EntityPopupCard
                :entity="item.entity"
                :lat-lng="item.latLng"
                @open="openEntity"
              />
            </LPopup>
          </LMarker>
        </EntityClusterGroup>
      </LMap>

      <div class="map-panel">
        <MapControlPanel
          v-model:search="search"
          v-model:datamodel="datamodel"
          :shown="placed.length"
          :total="total"
          :without-location="withoutLocation"
          :datamodels="datamodels"
          :datamodels-loading="datamodelsLoading"
        />
      </div>

      <div v-if="loading || locating" class="map-loading d-flex align-center ga-2 px-3 py-1">
        <VProgressCircular indeterminate color="primary" size="14" width="2" />
        <span class="text-caption text-medium-emphasis">
          {{ locating ? t('map.locating') : t('map.loading') }}
        </span>
      </div>

      <div
        v-if="showState"
        class="map-state d-flex align-center justify-center pa-4"
        :class="{ 'map-state--interactive': stateInteractive }"
      >
        <VCard class="map-state__card" elevation="6">
          <StateBlock
            :error="error"
            :empty="empty"
            :empty-text="emptyText"
            empty-icon="mdi-map-marker-off-outline"
            @retry="load"
          >
            <template #empty-action>
              <div class="d-flex flex-wrap justify-center ga-2">
                <VBtn
                  color="primary"
                  variant="tonal"
                  prepend-icon="mdi-crosshairs-gps"
                  :loading="locating"
                  @click="locateData"
                >
                  {{ t('map.locateData') }}
                </VBtn>
                <VBtn
                  v-if="filtered"
                  variant="tonal"
                  color="secondary"
                  prepend-icon="mdi-filter-remove-outline"
                  @click="clearFilters"
                >
                  {{ t('map.clearFilters') }}
                </VBtn>
              </div>
              <div v-if="locateFailed" class="text-caption text-medium-emphasis mt-3">
                {{ t('map.locateEmpty') }}
              </div>
            </template>
          </StateBlock>
        </VCard>
      </div>
    </div>

    <details class="map-alt mt-3">
      <summary class="map-alt__summary text-body-2">
        <VIcon icon="mdi-table" size="16" class="me-2" />
        {{ tableToggleText }}
      </summary>

      <VCard class="table-card mt-2">
        <VDataTable
          :headers="tableHeaders"
          :items="tableRows"
          :items-per-page="-1"
          :no-data-text="emptyText"
          item-value="id"
          height="240"
          density="compact"
          fixed-header
          hide-default-footer
          class="text-body-2"
        >
          <template #[`item.name`]="{ item }">
            <RouterLink
              :to="`/entidades/${item.id}`"
              class="text-primary font-weight-medium text-decoration-none"
            >
              {{ item.name }}
            </RouterLink>
          </template>
        </VDataTable>
      </VCard>

      <p class="text-caption text-medium-emphasis mt-2 mb-0">{{ t('map.table.caption') }}</p>
    </details>
  </div>
</template>

<style scoped>
/* La tabla equivalente vive fuera del lienzo: plegada ocupa una linea y el mapa conserva
   practicamente todo el alto; desplegada, se reparten el espacio. */
.map-alt__summary {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  color: rgb(var(--v-theme-on-surface-variant));
  user-select: none;
}

.map-alt__summary:hover {
  background: rgb(var(--v-theme-surface-variant));
}

.map-alt__summary:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

/* Alto util: el mapa ocupa lo que queda bajo la barra superior, descontando el relleno
   del contenedor de la aplicacion. Sin una altura explicita Leaflet no se dibuja. */
.map-view {
  height: calc(100vh - var(--v-layout-top, 64px) - 32px);
  height: calc(100dvh - var(--v-layout-top, 64px) - 32px);
  min-height: 420px;
}

@media (min-width: 960px) {
  .map-view {
    height: calc(100dvh - var(--v-layout-top, 64px) - 48px);
  }
}

.map-canvas {
  border: 1px solid rgb(var(--v-theme-outline));
}

/* El panel, el aviso de carga y los estados flotan por encima de los paneles de Leaflet
   (que llegan hasta z-index 800). */
.map-panel {
  position: absolute;
  inset-block-start: 12px;
  inset-inline-start: 12px;
  z-index: 900;
  width: calc(100% - 24px);
  max-width: 360px;
}

/* En pantalla estrecha el aviso se cuelga debajo de la barra plegada del panel. */
.map-loading {
  position: absolute;
  inset-block-start: 78px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  z-index: 910;
  border-radius: 999px;
  background: rgba(var(--v-theme-surface), 0.94);
  border: 1px solid rgb(var(--v-theme-outline));
  box-shadow: 0 2px 10px rgb(0 0 0 / 12%);
  white-space: nowrap;
  pointer-events: none;
}

/* En escritorio el panel solo ocupa la esquina: el centro de la franja superior queda libre. */
@media (min-width: 960px) {
  .map-loading {
    inset-block-start: 12px;
  }
}

.map-state {
  position: absolute;
  inset: 0;
  z-index: 880;
  pointer-events: none;
}

.map-state__card {
  width: 100%;
  max-width: 360px;
}

.map-state--interactive .map-state__card {
  pointer-events: auto;
}

/* Leaflet genera los marcadores, los globos de agrupacion, el bocadillo y sus controles como
   HTML propio: su aspecto no sale de props de Vuetify, asi que se reconduce aqui a los tokens
   del tema. Es la excepcion de la Regla 1, y tambien aqui los colores son tokens. */
:deep(.leaflet-container) {
  background: rgb(var(--v-theme-surface-variant));
  font-family: inherit;
}

:deep(.entity-marker),
:deep(.entity-cluster) {
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.entity-marker__dot) {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  border: 2px solid rgb(var(--v-theme-surface));
  box-shadow: 0 1px 4px rgb(0 0 0 / 35%);
  transition: transform 120ms ease-out;
}

:deep(.leaflet-marker-icon:hover .entity-marker__dot) {
  transform: scale(1.25);
}

:deep(.entity-cluster) {
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border: 2px solid rgb(var(--v-theme-surface));
  font-variant-numeric: tabular-nums;
}

/* El halo crece con el grupo: el tamaño del globo se lee incluso sin comparar los numeros. */
:deep(.entity-cluster--sm) {
  box-shadow: 0 1px 4px rgb(0 0 0 / 30%), 0 0 0 3px rgba(var(--v-theme-primary), 0.16);
}

:deep(.entity-cluster--md) {
  box-shadow: 0 1px 5px rgb(0 0 0 / 32%), 0 0 0 5px rgba(var(--v-theme-primary), 0.18);
}

:deep(.entity-cluster--lg) {
  box-shadow: 0 2px 6px rgb(0 0 0 / 34%), 0 0 0 7px rgba(var(--v-theme-primary), 0.2);
}

/* Un marcador pegado al panel abre su bocadillo hacia arriba, y con el orden de Leaflet
   (pane 700) quedaria escondido detras del panel. Se sube por encima: taparlo un momento es
   mejor que abrir una ficha que no se ve. */
:deep(.leaflet-popup-pane) {
  z-index: 920;
}

/* El bocadillo pone su propio relleno por defecto y deja el contenido apretado: se anula
   para que el espaciado lo ponga la ficha con las utilidades de siempre. */
:deep(.leaflet-popup-content-wrapper) {
  padding: 0;
  border-radius: 14px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border: 1px solid rgb(var(--v-theme-outline));
  box-shadow: 0 6px 20px rgb(0 0 0 / 18%);
}

:deep(.leaflet-popup-content) {
  margin: 0;
}

:deep(.leaflet-popup-tip) {
  background: rgb(var(--v-theme-surface));
  box-shadow: none;
}

:deep(.leaflet-container .leaflet-popup-close-button) {
  display: flex;
  align-items: center;
  justify-content: center;
  inset-block-start: 6px;
  inset-inline-end: 6px;
  width: 26px;
  height: 26px;
  padding: 0;
  border-radius: 50%;
  color: rgb(var(--v-theme-on-surface-variant));
}

:deep(.leaflet-container .leaflet-popup-close-button:hover),
:deep(.leaflet-container .leaflet-popup-close-button:focus-visible) {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface));
}

/* Zoom: los botones de Leaflet vienen con su propio blanco y su borde gris. */
:deep(.leaflet-control-zoom.leaflet-bar) {
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgb(0 0 0 / 14%);
}

:deep(.leaflet-control-zoom.leaflet-bar a) {
  width: 34px;
  height: 34px;
  line-height: 34px;
  font-family: inherit;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border-bottom: 1px solid rgb(var(--v-theme-outline));
}

:deep(.leaflet-control-zoom.leaflet-bar a:last-child) {
  border-bottom: none;
}

:deep(.leaflet-control-zoom.leaflet-bar a:hover),
:deep(.leaflet-control-zoom.leaflet-bar a:focus-visible) {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-primary));
}

:deep(.leaflet-control-zoom.leaflet-bar a.leaflet-disabled) {
  background: rgb(var(--v-theme-surface));
  color: rgba(var(--v-theme-on-surface), 0.38);
}

/* La atribucion es obligatoria por los terminos de uso de la cartografia: se le da fondo
   propio para que se lea en los dos temas, nunca transparencia sobre las teselas. */
:deep(.leaflet-container .leaflet-control-attribution) {
  padding: 3px 10px;
  border-start-start-radius: 10px;
  background: rgba(var(--v-theme-surface), 0.92);
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem; /* el tamaño de text-caption; 11px del paquete no se lee */
  box-shadow: none;
}

:deep(.leaflet-container .leaflet-control-attribution a) {
  color: rgb(var(--v-theme-primary));
}

/* Cartografia clara sobre tema oscuro: deslumbra. Se invierte y se recoloca el tono para
   obtener una capa nocturna sin depender de un servicio con clave. Solo afecta al panel de
   teselas; los marcadores viven en otro panel y conservan su color.

   PENDIENTE DE VERIFICACION DINAMICA — GDTIS-PT01-ACC-012 (WCAG 1.4.3).
   El filtro altera el contraste real de las ETIQUETAS CARTOGRAFICAS (nombres de calle y de
   barrio, que vienen pintados dentro de la propia tesela), y ese contraste no es calculable
   estaticamente: depende del pixel de cada tesela. Lo que hay que medir cuando exista entorno
   desplegado, y por que se deja asi mientras tanto:

     - Que medir: contraste de las etiquetas de tesela sobre su fondo, en tema oscuro y en los
       niveles de zoom de uso habitual (13 a 18), con un medidor sobre pixeles. El termino
       sospechoso es `contrast(0.88)`, que REDUCE el contraste de partida; si la medida no
       llega a 4.5:1, la correccion es subirlo hacia 1 y compensar el deslumbramiento con
       `brightness`, no al reves.
     - Por que no se cambia a ciegas: cualquier valor elegido sin medir es tan arbitrario como
       el actual, y tocarlo dejaria el tema oscuro peor sin evidencia de que mejora.
     - Que atenua el riesgo mientras tanto: ninguna informacion de la aplicacion vive solo en
       las etiquetas de la tesela. La atribucion tiene su propio fondo opaco (regla de arriba),
       los marcadores no pasan por el filtro, y desde esta subsanacion el area visible del mapa
       tiene ademas una tabla equivalente con nombre y coordenadas de cada entidad. */
.map-canvas--dark :deep(.leaflet-tile-pane) {
  filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.88) saturate(0.72);
}
</style>
