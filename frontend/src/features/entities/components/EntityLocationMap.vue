<script setup lang="ts">
import { LMap, LMarker, LTileLayer } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import { t } from '@/i18n'
import { tilesAttribution, tilesUrl } from '@/lib/mapConfig'

/**
 * Mapa de solo lectura con un unico marcador.
 *
 * La cartografia sale de `mapConfig`, no de `import.meta.env`: las variables VITE_* se sustituyen
 * por literales al compilar, asi que leerlas aqui se salta la configuracion que el contenedor
 * inyecta al arrancar y en un despliegue configurado por `config.js` las teselas salian en
 * blanco. Ademas `mapConfig` garantiza la atribucion, que es obligatoria por los terminos de uso
 * del proveedor de teselas.
 */
const props = withDefaults(
  defineProps<{
    lat: number
    lon: number
    zoom?: number
    height?: number
  }>(),
  { zoom: 16, height: 280 },
)

const tiles = tilesUrl()
const attribution = tilesAttribution()
</script>

<template>
  <!-- Leaflet necesita una altura explicita en su contenedor: sin ella el mapa no se dibuja. -->
  <div
    class="rounded-lg overflow-hidden"
    :style="{ height: `${props.height}px` }"
    role="group"
    :aria-label="t('entities.detail.mapLabel')"
  >
    <LMap
      :zoom="props.zoom"
      :center="[props.lat, props.lon]"
      :scroll-wheel-zoom="false"
      :style="{ height: '100%' }"
    >
      <LTileLayer :url="tiles" :attribution="attribution" />
      <LMarker :lat-lng="[props.lat, props.lon]" />
    </LMap>
  </div>
</template>
