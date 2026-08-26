import shared from './messages'
import occupancy from '../occupancy/i18n'
import classification from '../classification/i18n'
import heatmap from '../heatmap/i18n'
import transits from '../transits/i18n'

/**
 * Cada familia de plantillas aporta su fragmento y aqui se fusionan, de modo que tres personas
 * pueden trabajar en paralelo sin tocar el mismo fichero.
 */
export default { ...shared, ...occupancy, ...classification, ...heatmap, ...transits }
