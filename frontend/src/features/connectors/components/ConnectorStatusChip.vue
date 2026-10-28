<script setup lang="ts">
import { computed } from 'vue'
import { connectorStatus } from '../lib/display'
import type { ConnectorRow } from '../types'

const props = withDefaults(
  defineProps<{
    connector: Pick<ConnectorRow, 'status' | 'retries'>
    size?: string
  }>(),
  { size: 'small' },
)

const status = computed(() => connectorStatus(props.connector))
</script>

<template>
  <VChip
    :color="status.color"
    :size="size"
    :prepend-icon="status.icon"
    :title="status.hint"
    variant="tonal"
  >
    {{ status.label }}
  </VChip>
</template>
