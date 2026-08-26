<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'

/** Pie de tabla propio: el de la libreria trae sus textos en ingles. */
const props = withDefaults(
  defineProps<{
    page: number
    itemsPerPage: number
    total: number
    perPageOptions?: number[]
  }>(),
  { perPageOptions: () => [10, 25, 50] },
)

const emit = defineEmits<{
  'update:page': [value: number]
  'update:itemsPerPage': [value: number]
}>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.itemsPerPage)))

const rangeLabel = computed(() => {
  const first = props.total === 0 ? 0 : (props.page - 1) * props.itemsPerPage + 1
  const last = Math.min(props.page * props.itemsPerPage, props.total)
  return t('alarms.table.range', {
    from: formatNumber(first, 0),
    to: formatNumber(last, 0),
    total: formatNumber(props.total, 0),
  })
})

function changePerPage(value: unknown) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return
  emit('update:itemsPerPage', parsed)
  emit('update:page', 1)
}
</script>

<template>
  <VDivider />
  <div class="d-flex flex-wrap align-center ga-4 px-4 py-3">
    <div class="d-flex align-center ga-2">
      <span class="text-body-2 text-medium-emphasis">{{ t('common.rowsPerPage') }}</span>
      <VSelect
        :model-value="itemsPerPage"
        :items="perPageOptions"
        density="compact"
        max-width="104"
        :aria-label="t('common.rowsPerPage')"
        @update:model-value="changePerPage"
      />
    </div>

    <VSpacer />

    <div class="text-body-2 text-medium-emphasis">{{ rangeLabel }}</div>

    <div class="d-flex align-center ga-2">
      <VBtn
        icon="mdi-chevron-left"
        variant="text"
        density="comfortable"
        :disabled="page <= 1"
        :aria-label="t('alarms.table.prev')"
        @click="emit('update:page', page - 1)"
      />
      <VBtn
        icon="mdi-chevron-right"
        variant="text"
        density="comfortable"
        :disabled="page >= pageCount"
        :aria-label="t('alarms.table.next')"
        @click="emit('update:page', page + 1)"
      />
    </div>
  </div>
</template>
