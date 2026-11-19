<script setup lang="ts">
import { computed } from 'vue'
import { t } from '@/i18n'
import { datamodelInfo } from '../lib/datamodel'

const props = defineProps<{
  datamodel: string
  /** La ficha ya muestra a la vista la descripcion y el origen: aqui solo falta el nombre tecnico. */
  technicalOnly?: boolean
}>()

const info = computed(() => datamodelInfo(props.datamodel))
</script>

<template>
  <div class="d-flex flex-column ga-1">
    <template v-if="info && !technicalOnly">
      <div class="font-weight-medium">{{ info.label }}</div>
      <div>{{ info.description }}</div>
      <div>
        <span class="font-weight-medium">{{ t('entities.datamodel.source') }}:</span> {{ info.source }}
      </div>
    </template>
    <div class="text-caption">{{ t('entities.datamodel.technical', { name: datamodel }) }}</div>
  </div>
</template>
