<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatNumber } from '@/lib/format'
import { numericValue } from '../data'

const props = defineProps<{ value: unknown }>()

type Level = 'high' | 'medium' | 'low' | 'unknown'

const HIGH_WORDS = ['high', 'alta', 'alto', 'good', 'buena', 'reliable', 'fiable']
const MEDIUM_WORDS = ['medium', 'media', 'medio', 'moderate', 'moderada', 'fair']
const LOW_WORDS = ['low', 'baja', 'bajo', 'poor', 'pobre', 'unreliable']

const resolved = computed<{ level: Level; label: string }>(() => {
  const num = numericValue(props.value)
  if (num !== null) {
    const r = num > 1 ? num / 100 : num
    const level: Level = r >= 0.8 ? 'high' : r >= 0.5 ? 'medium' : 'low'
    return { level, label: `${formatNumber(r * 100, 0)} %` }
  }

  const text = String(props.value ?? '').trim().toLowerCase()
  if (HIGH_WORDS.includes(text)) return { level: 'high', label: t('dashboards.lidar.confidence.high') }
  if (MEDIUM_WORDS.includes(text)) return { level: 'medium', label: t('dashboards.lidar.confidence.medium') }
  if (LOW_WORDS.includes(text)) return { level: 'low', label: t('dashboards.lidar.confidence.low') }
  if (text) return { level: 'unknown', label: String(props.value) }
  return { level: 'unknown', label: t('common.noValue') }
})

const PRESENTATION: Record<Level, { color: string; icon: string }> = {
  high: { color: 'success', icon: 'mdi-shield-check-outline' },
  medium: { color: 'warning', icon: 'mdi-shield-alert-outline' },
  low: { color: 'error', icon: 'mdi-shield-off-outline' },
  unknown: { color: 'secondary', icon: 'mdi-shield-outline' },
}

const color = computed(() => PRESENTATION[resolved.value.level].color)
const icon = computed(() => PRESENTATION[resolved.value.level].icon)
const label = computed(() => resolved.value.label)
</script>

<template>
  <VChip :color="color" :prepend-icon="icon" variant="tonal" :title="t('dashboards.lidar.confidence.label')">
    {{ label }}
  </VChip>
</template>
