<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { formatDate, formatNumber, relativeFromNow } from '@/lib/format'
import { useSessionStore } from '@/stores/session'
import AlarmStateChip from './AlarmStateChip.vue'
import { alarmStatus, createdAt, type ActionChannel } from '../lib/display'
import type { AlarmDetail } from '../types'

const props = withDefaults(
  defineProps<{
    alarm: AlarmDetail
    thresholdCount: number
    inactivityCount: number
    channels: ActionChannel[]
    channelsUnavailable?: boolean
  }>(),
  { channelsUnavailable: false },
)

const session = useSessionStore()

const conditionCount = computed(() => props.thresholdCount + props.inactivityCount)

const conditionHint = computed(() => {
  const parts: string[] = []
  if (props.thresholdCount > 0) {
    parts.push(t('alarms.kpi.threshold', { count: formatNumber(props.thresholdCount, 0) }))
  }
  if (props.inactivityCount > 0) {
    parts.push(t('alarms.kpi.inactivity', { count: formatNumber(props.inactivityCount, 0) }))
  }
  return parts.length ? parts.join(' · ') : t('alarms.kpi.noConditions')
})

const channelCount = computed(() => props.channels.reduce((sum, one) => sum + one.count, 0))

const channelHint = computed(() => {
  if (props.channelsUnavailable) return t('alarms.kpi.channelsUnknown')
  if (!props.channels.length) return t('alarms.kpi.noChannels')
  return props.channels.map((channel) => channel.label).join(' · ')
})

const created = computed(() => createdAt(props.alarm))

interface Indicator {
  key: string
  label: string
  icon: string
  value?: string
  hint: string
}

const indicators = computed<Indicator[]>(() => [
  {
    key: 'state',
    label: t('alarms.kpi.state'),
    icon: 'mdi-bell-outline',
    hint: alarmStatus(props.alarm).hint,
  },
  {
    key: 'conditions',
    label: t('alarms.kpi.conditions'),
    icon: 'mdi-format-list-checks',
    value: formatNumber(conditionCount.value, 0),
    hint: conditionHint.value,
  },
  {
    key: 'channels',
    label: t('alarms.kpi.channels'),
    icon: 'mdi-send-outline',
    value: props.channelsUnavailable ? '—' : formatNumber(channelCount.value, 0),
    hint: channelHint.value,
  },
  {
    key: 'created',
    label: t('alarms.kpi.created'),
    icon: 'mdi-calendar-blank-outline',
    value: formatDate(created.value, session.timeZone),
    hint: relativeFromNow(created.value, session.timeZone),
  },
])
</script>

<template>
  <div class="d-flex flex-wrap ga-4">
    <VCard
      v-for="indicator in indicators"
      :key="indicator.key"
      class="flex-1-1-0"
      style="min-width: 150px"
    >
      <div class="pa-4">
        <div class="d-flex align-center ga-2 mb-3">
          <VIcon :icon="indicator.icon" size="16" class="text-medium-emphasis" />
          <span class="text-caption text-medium-emphasis text-truncate">{{ indicator.label }}</span>
        </div>

        <AlarmStateChip v-if="indicator.key === 'state'" :alarm="alarm" />
        <div v-else class="text-h6 font-weight-medium text-truncate" :title="indicator.value">
          {{ indicator.value }}
        </div>

        <div class="text-caption text-medium-emphasis text-truncate mt-2" :title="indicator.hint">
          {{ indicator.hint }}
        </div>
      </div>
    </VCard>
  </div>
</template>
