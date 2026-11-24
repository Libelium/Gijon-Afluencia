<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { provideExpanded } from '../charts/expanded'

/**
 * Marco que amplia una tarjeta a casi toda la pantalla. La tarjeta no se vuelve a montar: se
 * traslada tal cual, asi que no recarga sus datos ni pierde lo que se haya elegido en ella.
 */
const props = defineProps<{
  /** Nombre del dialogo cuando esta ampliada: el titulo de la tarjeta. */
  label: string
}>()

const FOCUSABLE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'

const expanded = ref(false)
const frame = ref<HTMLElement | null>(null)
/** Alto que ocupaba la tarjeta: se reserva para que la rejilla no salte mientras esta fuera. */
const reserved = ref(0)
let opener: HTMLElement | null = null

provideExpanded(expanded)

/** Dentro de la aplicacion, para conservar su tema; en las pruebas no existe y vale el body. */
function target(): string {
  return typeof document !== 'undefined' && document.querySelector('.v-application') ? '.v-application' : 'body'
}

function open() {
  reserved.value = frame.value?.offsetHeight ?? 0
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  expanded.value = true
}

function close() {
  expanded.value = false
  void nextTick(() => opener?.focus())
}

function toggle() {
  if (expanded.value) close()
  else open()
}

watch(expanded, async (value) => {
  document.documentElement.classList.toggle('expand-frame-open', value)
  await nextTick()
  if (value) frame.value?.focus()
  // Leaflet y ECharts escuchan el redimensionado de la ventana: asi recalculan su tamano en cuanto
  // la tarjeta ya esta colocada, ampliada o de vuelta en la rejilla.
  requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
})

function focusables(): HTMLElement[] {
  return [...(frame.value?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])].filter(
    (el) => !el.hasAttribute('disabled') && el.getClientRects().length > 0,
  )
}

/** Escape cierra y el tabulador no sale del marco mientras esta ampliado. */
function onKeydown(event: KeyboardEvent) {
  if (!expanded.value) return
  if (event.key === 'Escape') {
    event.stopPropagation()
    close()
    return
  }
  if (event.key !== 'Tab') return
  const items = focusables()
  if (!items.length) {
    event.preventDefault()
    return
  }
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement
  if (event.shiftKey && (active === first || active === frame.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

onBeforeUnmount(() => {
  if (expanded.value) document.documentElement.classList.remove('expand-frame-open')
})

defineExpose({ toggle, expanded })
</script>

<template>
  <div class="h-100" :style="expanded ? { minHeight: `${reserved}px` } : undefined">
    <Teleport :to="target()" :disabled="!expanded">
      <div v-if="expanded" class="expand-frame__scrim" @click="close" />
      <div
        ref="frame"
        class="expand-frame"
        :class="{ 'expand-frame--open': expanded }"
        :role="expanded ? 'dialog' : undefined"
        :aria-modal="expanded ? 'true' : undefined"
        :aria-label="expanded ? props.label : undefined"
        :tabindex="expanded ? -1 : undefined"
        @keydown="onKeydown"
      >
        <slot :expanded="expanded" :toggle="toggle" />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.expand-frame {
  block-size: 100%;
}

.expand-frame--open {
  position: fixed;
  inset: 24px;
  /* Por debajo de los menus y tooltips de Vuetify (2000), que se abren desde dentro. */
  z-index: 1901;
  block-size: auto;
  overflow: auto;
  outline: none;
  border-radius: 8px;
  box-shadow: 0 12px 40px rgb(0 0 0 / 35%);
}

.expand-frame__scrim {
  position: fixed;
  inset: 0;
  z-index: 1900;
  background: rgb(0 0 0 / 55%);
}

@media (max-width: 599px) {
  .expand-frame--open {
    inset: 8px;
  }
}
</style>

<style>
/* Con una tarjeta ampliada la pagina de detras no se desplaza. */
html.expand-frame-open {
  overflow: hidden;
}
</style>
