import { computed } from 'vue'
import { useDisplay } from 'vuetify'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { chartThemeFor } from './echartsTheme'

/**
 * Estado compartido por todos los graficos: tema registrado en ECharts, si la pantalla es
 * estrecha (leyenda abajo y menos marcas en los ejes) y la zona horaria del usuario.
 * Cada grafico lo consulta por su cuenta, asi que funciona igual dentro del renderizador
 * que usado de forma aislada.
 */
export function useChartTheme() {
  const ui = useUiStore()
  const session = useSessionStore()
  const { smAndDown } = useDisplay()

  return {
    themeName: computed(() => chartThemeFor(ui.theme)),
    isDark: computed(() => ui.theme === 'dark'),
    compact: smAndDown,
    timeZone: computed(() => session.timeZone),
  }
}
