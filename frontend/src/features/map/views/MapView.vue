<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { LMap, LMarker, LPopup, LTileLayer } from '@vue-leaflet/vue-leaflet'
import type { Map as LeafletMap } from 'leaflet'
import { errorMessage } from '@/api/http'
import { useDebouncedResize } from '@/composables/useDebouncedResize'
import { t } from '@/i18n'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import type { Bounds, Entity } from '@/types'
import { listDatamodels, listEntitiesInBounds, sampleEntities } from '../api/map'
import EntityClusterGroup from '../components/EntityClusterGroup.vue'
import EntityPopupCard from '../components/EntityPopupCard.vue'
import MapControlPanel from '../components/MapControlPanel.vue'
import { createEntityIcon } from '../lib/cluster'
import { boundsOf, placeEntities, type PlacedEntity } from '../lib/geometry'
import MapEntityTable from '../components/MapEntityTable.vue'
import { defaultCenter, defaultZoom, tilesForTheme } from '@/lib/mapConfig'

/** Tope de marcadores por vista: el mapa pide solo el area visible, nunca el inventario. */
const MAX_MARKERS = 300
const MOVE_DEBOUNCE_MS = 500
const FILTER_DEBOUNCE_MS = 400
const RESIZE_DEBOUNCE_MS = 160
// La cartografia se lee de `@/lib/mapConfig`, que consulta la configuracion inyectada por el
// contenedor antes de la incrustada al compilar: asi se puede cambiar el proveedor de teselas
// en el despliegue sin reconstruir la imagen. La atribucion es obligatoria por su licencia.

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
const tiles = computed(() => tilesForTheme(dark.value))
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
          :url="tiles.url"
          :attribution="tiles.attribution"
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

    <MapEntityTable :placed="placed" :empty-text="emptyText" />
  </div>
</template>

<style scoped src="./MapView.css"></style>
