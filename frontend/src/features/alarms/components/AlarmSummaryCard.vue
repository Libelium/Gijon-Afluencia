<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { conditionLines, conditionsIntro } from '../lib/conditions'
import type { ActionChannel } from '../lib/display'
import type { AlarmDetail, InactivityCondition, ThresholdCondition } from '../types'

const props = withDefaults(
  defineProps<{
    alarm: AlarmDetail
    conditions?: ThresholdCondition[]
    inactivityConditions?: InactivityCondition[]
    channels?: ActionChannel[]
    channelsUnavailable?: boolean
  }>(),
  {
    conditions: () => [],
    inactivityConditions: () => [],
    channels: () => [],
    channelsUnavailable: false,
  },
)

const lines = computed(() => conditionLines(props.conditions, props.inactivityConditions))

const intro = computed(() => conditionsIntro(props.alarm.function, lines.value.length))
</script>

<template>
  <VCard>
    <div class="pa-4 pa-md-6">
      <div class="text-subtitle-2 mb-4">{{ t('alarms.summary.title') }}</div>

      <template v-if="lines.length">
        <p class="text-body-2 text-medium-emphasis mb-4">{{ intro }}</p>

        <div class="d-flex flex-column ga-4">
          <div v-for="line in lines" :key="line.key" class="d-flex align-start ga-3">
            <VIcon :icon="line.icon" size="18" class="text-primary flex-shrink-0" />
            <div class="min-w-0">
              <!-- Texto plano: los nombres de entidad y medida vienen del servidor sin sanear. -->
              <div class="text-body-2">{{ line.subject }} <span class="font-weight-medium">{{ line.operator }}</span>.</div>
              <div v-if="line.period" class="text-caption text-medium-emphasis mt-1">
                {{ line.period }}
              </div>
            </div>
          </div>
        </div>
      </template>

      <p v-else class="text-body-2 text-medium-emphasis mb-0">
        {{ t('alarms.summary.noConditions') }}
      </p>

      <VDivider class="my-6" />

      <div class="text-subtitle-2 mb-3">{{ t('alarms.summary.actions') }}</div>

      <div v-if="channels.length" class="d-flex flex-wrap ga-2">
        <VChip
          v-for="channel in channels"
          :key="channel.label"
          :prepend-icon="channel.icon"
          variant="tonal"
        >
          {{ channel.count > 1 ? `${channel.label} (${channel.count})` : channel.label }}
        </VChip>
      </div>
      <p v-else class="text-body-2 text-medium-emphasis mb-0">
        {{ channelsUnavailable ? t('alarms.summary.actionsUnavailable') : t('alarms.summary.noActions') }}
      </p>
    </div>
  </VCard>
</template>
