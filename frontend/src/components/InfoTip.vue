<script setup lang="ts">
defineProps<{
  /** Lo que anuncia el lector de pantalla: «Información sobre …». */
  label: string
}>()
</script>

<template>
  <!-- Un boton y no un icono suelto: se llega con el teclado, y el emergente se abre al enfocarlo.
       No deja pasar el clic ni la tecla: en una fila que enlaza a otra pagina, pulsarlo no debe navegar. -->
  <VTooltip location="top" max-width="380">
    <template #activator="{ props: tip }">
      <VBtn
        v-bind="tip"
        icon="mdi-information-outline"
        variant="text"
        density="compact"
        size="x-small"
        class="text-medium-emphasis flex-shrink-0"
        :aria-label="label"
        @click.stop
        @keydown.enter.stop
        @keydown.space.stop
      />
    </template>
    <slot />
  </VTooltip>
</template>
