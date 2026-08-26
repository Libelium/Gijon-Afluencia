# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv

# La directiva de arriba silencia un falso positivo, y va pegada a `syntax` porque las
# directivas del analizador tienen que ir antes de cualquier comentario: marca todo ARG
# cuyo nombre acabe en KEY como posible secreto, y VITE_DATA_SCOPE_PREFERENCE_KEY es la
# clave de una preferencia de usuario del backend. Ninguna VITE_* puede llevar secretos:
# todas acaban en el JavaScript que descarga el navegador.

# Imagen de PID-GIJON: compila el paquete estatico y lo sirve con nginx.
# Dos etapas, para que la imagen final no arrastre Node ni las dependencias de compilacion.

# ---------------------------------------------------------------------------
# Etapa 1 — compilacion
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Las dependencias van en su propia capa: solo se reinstalan si cambia el manifiesto.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Las variables VITE_* se incrustan en el paquete al compilar: no se leen en tiempo de
# ejecucion. Se aceptan aqui como argumentos de construccion para poder generar un
# artefacto valido con el codigo actual. El fichero config.js que escribe
# deploy/entrypoint.sh es el mecanismo previsto para sustituirlas y permitir reutilizar
# una misma imagen en varios entornos; ver la seccion «Pendiente» de docs/deployment.md.
ARG VITE_API_BASE_URL=""
ARG VITE_OIDC_URL=""
ARG VITE_OIDC_REALM=""
ARG VITE_OIDC_CLIENT_ID=""
ARG VITE_OIDC_REDIRECT_URI=""
ARG VITE_MAP_TILES_URL="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ARG VITE_MAP_TILES_ATTRIBUTION="&copy; colaboradores de OpenStreetMap"
ARG VITE_MAP_DEFAULT_CENTER="43.5322,-5.6611"
ARG VITE_MAP_DEFAULT_ZOOM="13"
ARG VITE_REALTIME_URL=""
ARG VITE_DATA_SCOPE_PREFERENCE_KEY=""
ARG VITE_ALARM_ENTITY_TYPE=""

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_OIDC_URL=$VITE_OIDC_URL \
    VITE_OIDC_REALM=$VITE_OIDC_REALM \
    VITE_OIDC_CLIENT_ID=$VITE_OIDC_CLIENT_ID \
    VITE_OIDC_REDIRECT_URI=$VITE_OIDC_REDIRECT_URI \
    VITE_MAP_TILES_URL=$VITE_MAP_TILES_URL \
    VITE_MAP_TILES_ATTRIBUTION=$VITE_MAP_TILES_ATTRIBUTION \
    VITE_MAP_DEFAULT_CENTER=$VITE_MAP_DEFAULT_CENTER \
    VITE_MAP_DEFAULT_ZOOM=$VITE_MAP_DEFAULT_ZOOM \
    VITE_REALTIME_URL=$VITE_REALTIME_URL \
    VITE_DATA_SCOPE_PREFERENCE_KEY=$VITE_DATA_SCOPE_PREFERENCE_KEY \
    VITE_ALARM_ENTITY_TYPE=$VITE_ALARM_ENTITY_TYPE

# `npm run build` es `vue-tsc --noEmit && vite build`: si la comprobacion de tipos falla,
# la construccion de la imagen falla. Es deliberado, y por eso npm ci instala tambien las
# dependencias de desarrollo (NODE_ENV no se fija a production en esta etapa).
RUN npm run build

# ---------------------------------------------------------------------------
# Etapa 2 — servicio
# ---------------------------------------------------------------------------
FROM nginx:alpine AS runtime

ARG APP_VERSION="0.1.0"
ARG VCS_REF=""
ARG BUILD_DATE=""

LABEL org.opencontainers.image.title="PID Gijón" \
      org.opencontainers.image.description="Visualizador de datos de sensores urbanos: business intelligence y dashboards de análisis de datos." \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.created="$BUILD_DATE"

# Los permisos se fijan explicitamente: COPY conserva los del fichero de origen, y en un
# equipo con umask restrictiva quedan sin lectura para «otros». Como el contenedor no corre
# como root, nginx no podria leer su propia configuracion ni ejecutar el entrypoint.
COPY --chmod=0644 deploy/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=0644 deploy/security-headers.conf /etc/nginx/security-headers.conf
COPY --chmod=0755 deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --from=build --chown=nginx:nginx /app/dist/ /usr/share/nginx/html/

# El entrypoint escribe config.js dentro del directorio servido, y nginx escribe su pid y
# sus temporales en /var/cache/nginx: el usuario del contenedor necesita escritura en ambos.
# El chown va DESPUES de `nginx -t` a proposito: la validacion corre como root y crea ahi el
# pid y los directorios temporales, que de otro modo quedarian sin permisos para nginx.
RUN nginx -t \
    && chown nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx

USER nginx

# 8080 y no 80: un usuario que no es root no puede abrir puertos por debajo de 1024.
# El valor esta fijado en deploy/nginx.conf.
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --spider --tries=1 http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
