# Política de seguridad

Cómo comunicar una vulnerabilidad de la Plataforma de Integración de Datos del Ayuntamiento de
Gijón. La gestión de secretos del despliegue es otra cosa y está en
[`deploy/SECURITY.md`](deploy/SECURITY.md).

## Cómo informar de una vulnerabilidad

**No abras una incidencia pública para comunicar una vulnerabilidad.** Una incidencia es visible
para cualquiera desde el primer segundo, y eso deja expuestos los despliegues en producción antes
de que exista una corrección.

Envía la información por correo electrónico a la dirección de contacto del proyecto que figura en
el repositorio de publicación del Ayuntamiento de Gijón. Si has firmado un contrato de soporte, usa
además el canal previsto en él.

Si el problema afecta a un despliegue municipal en funcionamiento —no solo al código—, indícalo en
el asunto: eso cambia la prioridad.

### Qué incluir

Cuanto más concreto, antes se corrige:

- Descripción del problema y del impacto que crees que tiene.
- Componente afectado, y versión o revisión (etiqueta, o `commit` si lo sabes). Si es de la interfaz
  web, indica también el navegador.
- Pasos reproducibles, con el mínimo imprescindible.
- Prueba de concepto, si la tienes, y capturas o trazas de red que la respalden.
- Si sabes cómo corregirlo, tu propuesta.

**No incluyas datos personales reales, ni tokens, ni credenciales** en el informe. Si necesitas
demostrar el problema con datos, redáctalos u ofrécete a enseñarlo en una sesión.

### Qué puedes esperar

| Plazo | Compromiso |
| --- | --- |
| 5 días laborables | Acuse de recibo del informe |
| 15 días laborables | Valoración: si se confirma, su gravedad y un plan |
| Según gravedad | Corrección publicada, y aviso a los despliegues conocidos |

Se te dará crédito por el hallazgo en las notas de la versión que lo corrija, salvo que prefieras
permanecer anónimo. Pedimos que no hagas público el detalle hasta que exista una versión corregida
disponible; si el proceso se alarga sin justificación, avísanos antes de publicar.

## Alcance

Este repositorio contiene **la plataforma completa**, una carpeta por componente: la API de gestión
([`backend`](backend)), la ingesta ([`fiware-manager`](fiware-manager)), la capa de acceso al núcleo
FIWARE ([`aether-link`](aether-link)), la flota de consumidores
([`queues-consumer`](queues-consumer)), el módulo de predicción ([`predictions`](predictions)), la
configuración de identidad ([`keycloak`](keycloak)), la interfaz web ([`frontend`](frontend)) y el
despliegue ([`deploy`](deploy)). Todo eso está dentro del alcance.

### Dentro del alcance

**API de gestión y ingesta** (`backend`, `fiware-manager`, `aether-link`):

- Salto de autenticación o de autorización: rutas sin la comprobación que les corresponde, políticas
  que no se aplican, validación insuficiente del JWT del realm.
- Acceso a datos de otra organización, otro *tenant* o otro ámbito del que corresponde a la sesión.
- Inyección en cualquiera de sus formas —SQL, NGSI-LD, comandos, plantillas—, deserialización
  insegura y SSRF a través de parámetros que terminan en una petición saliente.
- Subida y descarga de ficheros: recorrido de rutas, tipo no validado, acceso al almacén de objetos
  sin autorización.
- Caminos de ingesta alcanzables sin credencial que deberían exigirla, incluido el archivado de la
  trama LIDAR y el proxy hacia el IoT Agent.

**Consumidores y procesos periódicos** (`queues-consumer`, `predictions`):

- Ejecución de código o escritura fuera de lo previsto a partir del contenido de un mensaje de cola
  o de un fichero del almacén de objetos.

**Identidad** (`keycloak`): configuración del realm, flujos de acceso y de segundo factor, y la
extensión de MFA por correo que se empaqueta en la imagen.

**Cliente web** (`frontend`):

- Ejecución de código en el cliente por datos no saneados que llegan de la API (XSS).
- Manejo incorrecto de tokens o de la sesión: fuga a registros, a la URL, a almacenamiento
  inadecuado, o cierre de sesión que no invalida realmente.
- Fallos del flujo OIDC tal y como lo usa esta aplicación (PKCE, URI de redirección, renovación).
- Exposición de información sensible en el artefacto construido: secretos incrustados en el
  paquete, restos de configuración de un despliegue.
- Enrutado o navegación que muestre a una persona datos de un ámbito al que no debería llegar
  **desde el cliente**.

**Despliegue** (`deploy`): charts o scripts que expongan un servicio que no debería salir al
exterior, que dejen una credencial en un sitio legible, o que concedan permisos de clúster más
amplios de lo necesario.

Y, en cualquier componente, **dependencias con vulnerabilidades conocidas que afecten de verdad** al
código que se despliega.

### Fuera del alcance

- **Los componentes de terceros que la plataforma despliega sin modificar**: Orion-LD, el IoT Agent,
  MongoDB, PostgreSQL/TimescaleDB, RabbitMQ, MinIO y el propio producto Keycloak. Comunica el
  hallazgo a su proyecto. Sí nos interesa, y sí está dentro del alcance, cuando lo que expone el
  problema es **la configuración que hace esta plataforma** de uno de ellos.
- La configuración de un despliegue concreto que opera un tercero: cabeceras HTTP, TLS, CORS,
  política de contenido, reglas de red. Son responsabilidad de quien lo opera; hay recomendaciones
  en [`deploy/docs`](deploy/docs) y en
  [`frontend/docs/deployment.md`](frontend/docs/deployment.md).
- Que la interfaz muestre un botón que la API acaba rechazando. **La autorización es del servidor**;
  ocultar controles en el cliente es cortesía, no un control de seguridad, y su ausencia no es una
  vulnerabilidad.
- Informes generados por un escáner automático sin comprobar que el problema es explotable aquí.
- Ingeniería social, denegación de servicio por volumen y ataques físicos.

## Prácticas del cliente web

Lo que ya hace el código de [`frontend`](frontend), para que no se informe como hallazgo y para que
no se rompa al modificarlo. El tratamiento de secretos del despliegue está en
[`deploy/SECURITY.md`](deploy/SECURITY.md):

- **Ningún secreto en el repositorio.** Solo entran URL, identificadores públicos de cliente OIDC y
  parámetros de mapa, todos por variables `VITE_*`. `.env` está fuera del control de versiones;
  solo se publica `.env.example`. Recuerda que **todo lo que empieza por `VITE_` acaba en el
  paquete que descarga el navegador**: nunca pongas ahí una credencial.
- **OIDC con PKCE (`S256`)** y tokens **en memoria**, gestionados por el cliente OIDC. No se
  escriben tokens en `localStorage` desde el código de la aplicación.
- **Renovación centralizada** con reintento único ante un 401 y cierre de sesión si el refresco
  falla, en `src/api/http.ts`.
- **Sin `v-html`** sobre contenido que venga de la API. Vue escapa la interpolación; introducir
  `v-html` con datos remotos abre un XSS.
- **Comprobación de tipos estricta** —`vue-tsc` en modo `strict`, plantillas incluidas— antes de
  publicar: un artefacto que no compila limpio no se publica.

Antes de proponer un cambio, repasa esa lista: la mayoría de los problemas de seguridad de un
cliente web entran por relajar uno de esos puntos.
