<script setup lang="ts">
import { computed } from 'vue'
import InfoTip from '@/components/InfoTip.vue'
import { t } from '@/i18n'
import type { Entity } from '@/types'
import { datamodelIcon, datamodelInfo, datamodelLabel } from '../lib/datamodel'
import CopyButton from './CopyButton.vue'
import DatamodelExplanation from './DatamodelExplanation.vue'

const props = defineProps<{ entity: Entity }>()

const info = computed(() => datamodelInfo(props.entity.datamodel))
</script>

<template>
  <VCard>
    <div class="d-flex align-center ga-2 px-4 pt-4 pb-3">
      <VIcon icon="mdi-identifier" size="18" class="text-medium-emphasis" />
      <span class="text-subtitle-2 font-weight-medium">{{ t('entities.detail.identity') }}</span>
    </div>

    <VDivider />

    <VList density="comfortable" class="py-0">
      <VListItem class="py-3">
        <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.detail.urn') }}</div>
        <div class="d-flex align-center ga-2 min-w-0">
          <span class="text-body-2 text-break flex-grow-1 min-w-0">
            {{ entity.urn || t('common.noValue') }}
          </span>
          <CopyButton
            v-if="entity.urn"
            :value="entity.urn"
            :label="t('entities.detail.copyUrn')"
          />
        </div>
      </VListItem>

      <VDivider />

      <VListItem class="py-3">
        <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.detail.internalId') }}</div>
        <div class="text-body-2">{{ entity.id }}</div>
      </VListItem>

      <VDivider />

      <VListItem class="py-3">
        <div class="text-caption text-medium-emphasis mb-2">{{ t('entities.detail.datamodel') }}</div>
        <template v-if="entity.datamodel">
          <div class="d-flex align-center ga-1">
            <VChip
              variant="tonal"
              color="secondary"
              :prepend-icon="datamodelIcon(entity.datamodel)"
              :text="datamodelLabel(entity.datamodel)"
            />
            <InfoTip :label="t('entities.datamodel.info', { name: datamodelLabel(entity.datamodel) })">
              <DatamodelExplanation :datamodel="entity.datamodel" technical-only />
            </InfoTip>
          </div>
          <!-- Que es cada tipo no se deduce de su nombre: en la ficha se dice a la vista. -->
          <template v-if="info">
            <div class="text-body-2 mt-2">{{ info.description }}</div>
            <div class="text-caption text-medium-emphasis mt-1">
              {{ t('entities.datamodel.source') }}: {{ info.source }}
            </div>
          </template>
        </template>
        <div v-else class="text-body-2 text-medium-emphasis">{{ t('common.noValue') }}</div>
      </VListItem>

      <VDivider />

      <VListItem class="py-3">
        <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.detail.tenant') }}</div>
        <div class="text-body-2">{{ entity.tenant || t('common.noValue') }}</div>
      </VListItem>

      <VDivider />

      <VListItem class="py-3">
        <div class="text-caption text-medium-emphasis mb-1">{{ t('entities.detail.scope') }}</div>
        <div class="text-body-2">{{ entity.scope || t('common.noValue') }}</div>
      </VListItem>
    </VList>
  </VCard>
</template>
