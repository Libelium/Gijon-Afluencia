<script setup lang="ts">
import { computed } from 'vue'
import { alarmStatus } from '../lib/display'
import type { AlarmRow } from '../types'

/** Un solo chip por alarma: los tres estados son excluyentes y asi no se confunden entre si. */
const props = withDefaults(
  defineProps<{
    alarm: Pick<AlarmRow, 'disabled' | 'up'>
    size?: string
  }>(),
  { size: 'small' },
)

const status = computed(() => alarmStatus(props.alarm))
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
