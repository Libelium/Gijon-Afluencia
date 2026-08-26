<script setup lang="ts">
import { computed } from 'vue'
import { alarmTypeLabel } from '../lib/display'

/** Chip neutro: el tipo clasifica, no avisa de nada, y no debe competir con el estado. */
const props = withDefaults(defineProps<{ type?: string; size?: string }>(), { size: 'small' })

const label = computed(() => alarmTypeLabel(props.type))
</script>

<template>
  <VChip :size="size" variant="tonal">{{ label }}</VChip>
</template>
