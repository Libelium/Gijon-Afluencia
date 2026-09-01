<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { useCustomizationStore } from '@/stores/customization'

/**
 * Pie de pagina personalizable por organizacion (preferencia `themeCustomFooter`).
 *
 * El HTML llega ya saneado por el backend con la lista blanca de HTMLPurifier, y aqui se vuelve a
 * sanear al pintar. No es redundancia inutil: el valor viaja por la API y podria haberse escrito
 * por otra via (una migracion, un script, una version anterior del validador), asi que el ultimo
 * punto antes de `v-html` tambien filtra. Es la misma defensa en profundidad que describe
 * `HtmlSanitizerHelper` en el backend.
 *
 * La lista de etiquetas es deliberadamente mas estrecha que la del servidor: aqui solo hace falta
 * texto con formato, enlaces e imagenes, que es lo que un pie de pagina necesita de verdad.
 */
const customization = useCustomizationStore()

const ALLOWED_TAGS = [
  'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'sub', 'sup',
  'ul', 'ol', 'li', 'span', 'div', 'a', 'img', 'figure',
  'table', 'thead', 'tbody', 'tr', 'td', 'th',
]

const ALLOWED_ATTR = ['href', 'title', 'target', 'rel', 'src', 'alt', 'width', 'height', 'style', 'class']

const safeHtml = computed(() => {
  const raw = customization.footerHtml
  if (!raw) return ''
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    // Solo esquemas inertes. `data:` se permite porque los logotipos del pie van incrustados en
    // base64, y la expresion limita esa via a imagenes rasterizadas.
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|data:image\/(?:png|jpeg|gif|webp);base64,)/i,
    // Nunca queremos que el pie escape de su contenedor ni cargue nada externo activo.
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['srcset', 'formaction', 'ping'],
  })
})
</script>

<script lang="ts">
/**
 * Todo enlace del pie sale fuera y sin filtrar el referente. `target="_blank"` sin
 * `rel="noopener"` deja que la pestana abierta acceda a `window.opener`.
 *
 * Va como gancho de DOMPurify y no recorriendo el DOM despues de pintar: el gancho corre en cada
 * saneado, asi que tambien cubre el HTML que cambia en caliente al guardar desde Personalizacion.
 * Se registra una sola vez a nivel de modulo — los ganchos de DOMPurify son globales y
 * registrarlos por instancia los acumularia.
 */
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.nodeName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})
</script>

<template>
  <VFooter v-if="safeHtml" class="app-footer px-4" border>
    <!-- eslint-disable-next-line vue/no-v-html -- saneado arriba con DOMPurify -->
    <div class="app-footer__content text-caption text-medium-emphasis" v-html="safeHtml" />
  </VFooter>
</template>

<style scoped>
/*
 * Alto FIJO, no dependiente del contenido.
 *
 * El HTML del pie lo escribe quien personaliza, asi que su alto natural es impredecible: una tira
 * de logotipos, dos parrafos o una imagen sin `height` declarado darian a cada despliegue un pie
 * de distinta altura, y el area de contenido saltaria al navegar entre paginas. Con un alto fijo,
 * la maquetacion es la misma en todas y el contenido se adapta al hueco en vez de al contrario.
 *
 * Se expone como variable para poder cambiarlo en un sitio. 72 px = los 48 px de la tira de
 * logotipos de financiacion mas 12 px de aire por arriba y por abajo.
 */
.app-footer {
  --app-footer-height: 72px;

  /* Las tres a la vez: Vuetify fija su propio `min-height` en VFooter, y sin anular tanto el
     minimo como el maximo el alto declarado no se respeta. */
  block-size: var(--app-footer-height);
  min-block-size: var(--app-footer-height);
  max-block-size: var(--app-footer-height);

  /* El contenido se centra en el hueco: cualquiera que sea su alto, queda a media altura y no
     pegado al borde superior. */
  display: flex;
  align-items: center;
  padding-block: 0;

  background: rgb(var(--v-theme-surface));
}

.app-footer__content {
  inline-size: 100%;
  /* Nunca mas alto que el pie: lo que no cabe se desplaza dentro de su caja, en vez de
     desbordarse por encima del contenido de la pagina. */
  max-block-size: 100%;
  overflow: auto;
}

/* El pie lo escribe quien personaliza: las imagenes tienen que caber sin desbordar la pagina,
   pase lo que pase con el ancho o el alto declarados en el HTML. El limite de alto es lo que
   hace que el alto fijo se sostenga: una imagen con `height:200px` se reduce en vez de estirar
   el pie o quedarse recortada. */
.app-footer__content :deep(img) {
  max-inline-size: 100%;
  max-block-size: calc(var(--app-footer-height) - 16px);
  block-size: auto;
  inline-size: auto;
  object-fit: contain;
  vertical-align: middle;
}

.app-footer__content :deep(p) {
  margin-bottom: 0;
}

.app-footer__content :deep(a) {
  color: rgb(var(--v-theme-primary));
}
</style>
