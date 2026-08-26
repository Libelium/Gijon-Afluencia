<script setup lang="ts">
import { inject, onBeforeUnmount, onMounted, provide } from 'vue'
import { InjectionKeys } from '@vue-leaflet/vue-leaflet'
import { createClusterGroup } from '../lib/cluster'

/**
 * El envoltorio de Vue para Leaflet no trae grupo de agrupacion por proximidad, pero si
 * publica las claves con las que una capa registra a sus hijos: creando el grupo con la API
 * de Leaflet y reemplazando esas claves, los marcadores declarados en la plantilla entran
 * en el grupo en lugar de ir directos al mapa.
 */
const group = createClusterGroup()

const addToMap = inject(InjectionKeys.AddLayerInjection)
const removeFromMap = inject(InjectionKeys.RemoveLayerInjection)

provide(InjectionKeys.AddLayerInjection, (layer) => {
  if (layer?.leafletObject) group.addLayer(layer.leafletObject)
})

provide(InjectionKeys.RemoveLayerInjection, (layer) => {
  if (layer?.leafletObject) group.removeLayer(layer.leafletObject)
})

// El grupo se añade al mapa despues de que los marcadores hijos se hayan registrado en el.
onMounted(() => addToMap?.({ leafletObject: group }))

onBeforeUnmount(() => {
  removeFromMap?.({ leafletObject: group })
  group.clearLayers()
})

defineExpose({ leafletObject: group })
</script>

<template>
  <slot />
</template>
