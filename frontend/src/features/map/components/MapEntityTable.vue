<script setup lang="ts">
/**
 * Ruta equivalente al mapa, en forma de tabla (WCAG 1.1.1 y 2.1.1).
 *
 * Un mapa de marcadores no se puede recorrer con el teclado de forma util —Leaflet dibuja los
 * marcadores agrupados y el globo emergente se abre sobre el lienzo—, y para un lector de
 * pantalla el mapa es un `<canvas>` de teselas. La alimenta la misma consulta que pinta los
 * marcadores, asi que lo que se lista es EXACTAMENTE lo que se ve, se actualiza con el encuadre
 * y cada fila lleva su enlace al detalle: es la ruta equivalente completa.
 */
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber, urnTail } from '@/lib/format'
import type { PlacedEntity } from '../lib/geometry'

const props = defineProps<{ placed: PlacedEntity[]; emptyText: string }>()

const headers = [
  { title: t('map.table.name'), key: 'name', sortable: false },
  { title: t('map.table.datamodel'), key: 'datamodel', sortable: false },
  { title: t('map.table.coordinates'), key: 'coordinates', sortable: false },
]

const rows = computed(() =>
  props.placed.map((item) => ({
    id: item.entity.id,
    name: item.entity.name || urnTail(item.entity.urn),
    datamodel: item.entity.datamodel || t('common.noValue'),
    coordinates: `${formatNumber(item.latLng[0], 5)}, ${formatNumber(item.latLng[1], 5)}`,
  })),
)

const toggleText = computed(() => {
  if (!props.placed.length) return t('map.table.toggleEmpty')
  if (props.placed.length === 1) return t('map.table.toggleOne')
  return t('map.table.toggle', { n: formatNumber(props.placed.length, 0) })
})
</script>

<template>
  <details class="map-alt mt-3">
    <summary class="map-alt__summary text-body-2">
      <VIcon icon="mdi-table" size="16" class="me-2" />
      {{ toggleText }}
    </summary>

    <VCard class="table-card mt-2">
      <VDataTable
        :headers="headers"
        :items="rows"
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
</template>

<style scoped>
/* Plegada ocupa una linea y el mapa conserva practicamente todo el alto; desplegada, se
   reparten el espacio. */
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
</style>
