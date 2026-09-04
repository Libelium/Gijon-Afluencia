FROM php:8.2-apache-bookworm
# OFFICIAL IMAGE FROM https://hub.docker.com/_/php/

# User and Groups ID for mapping directories
ARG UID=1001
ARG GID=1001
ARG WITH_XDEBUG=false

# Use the default production configuration
# --chmod: COPY preserva el modo de origen, y con un umask restrictivo el fichero llega
# sin permiso de lectura para www-data, que es quien corre el proceso.
COPY --chmod=644 php.ini $PHP_INI_DIR/conf.d/

# Hide PHP version from headers
RUN echo 'expose_php = Off' >> $PHP_INI_DIR/conf.d/php.ini

RUN find /etc/apt/sources.list.d/ -type f -print0 | xargs -0 sed -i 's/http:/https:/g'

# Patch base OS + Apache to the latest Debian security release, then install build deps.
# `apt-get upgrade` is what keeps Apache current (the php:8.2-apache base ships 2.4.65);
# without it the image stays on the base Apache and re-fails the Qualys/PCI scan.
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y \
    libicu-dev \
    libpq-dev \
    libsodium-dev \
    libzip-dev \
    zlib1g-dev \
    zip \
    ca-certificates \
    git \
    libpng-dev \
    libjpeg-dev \
    libcap2-bin \
    && rm -r /var/lib/apt/lists/*

RUN docker-php-ext-configure pdo_mysql --with-pdo-mysql=mysqlnd
RUN docker-php-ext-configure gd --with-jpeg

RUN docker-php-ext-install \
    gd \
    intl \
    pcntl \
    pdo_mysql \
    pdo_pgsql \
    pgsql \
    zip \
    opcache \
    bcmath \
    sockets \
    && docker-php-ext-enable sodium

RUN if [ $WITH_XDEBUG = "true" ] ; then \
    pecl install xdebug; \
    docker-php-ext-enable xdebug; \
    echo "error_reporting = E_ALL" >> /usr/local/etc/php/conf.d/docker-php-ext-xdebug.ini; \
    echo "display_startup_errors = On" >> /usr/local/etc/php/conf.d/docker-php-ext-xdebug.ini; \
    echo "display_errors = On" >> /usr/local/etc/php/conf.d/docker-php-ext-xdebug.ini; \
    echo "xdebug.mode=debug" >> /usr/local/etc/php/conf.d/docker-php-ext-xdebug.ini; \
    #        echo "xdebug.profiler_enable=1" >> /usr/local/etc/php/conf.d/docker-php-ext-xdebug.ini; \
    fi

# Change uid and gid of apache to docker user uid/gid
RUN usermod -u $UID www-data && groupmod -g $GID www-data

# COMPOSER INSTALL
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/bin --filename=composer

# Put apache config for Laravel
COPY --chmod=644 apache2-laravel.conf /etc/apache2/sites-available/laravel.conf

# Apache rewrite + security headers
RUN a2dissite 000-default.conf && a2ensite laravel.conf && a2enmod rewrite && a2enmod headers

COPY --chown=www-data:www-data ./src /var/www/html
COPY --chmod=755 --chown=www-data:www-data ./src/migration.sh /var/www/html/migration.sh
COPY --chown=www-data:www-data ./libelium_devices_fiware_datamodels/*.csv /var/www/html/storage/app/CSV/devices/

RUN rm /var/www/html/storage/app/CSV/devices/*sensor*

WORKDIR /var/www/html

EXPOSE 80

# El contenedor ya no vuelve a root, y sin ser root Apache no puede abrir el 80: se le da la
# capacidad al binario y se le dejan escribibles los directorios que usa el entrypoint. Bajar
# el puerto no vale: el 80 es el que esperan los charts y los compose.
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/apache2 \
    && apt-get purge -y libcap2-bin \
    && mkdir -p /var/run/apache2 /var/lock/apache2 /var/log/apache2 \
    && chown -R www-data:www-data /var/run/apache2 /var/lock/apache2 /var/log/apache2

# compile app and serve for production

# Numerico y no `www-data`: con `runAsNonRoot: true` kubelet solo puede verificar que el
# usuario de la imagen no es root si viene por uid.
USER $UID:$GID

# `install` y NUNCA `update`: install resuelve desde el composer.lock versionado,
# que viaja en el COPY ./src de arriba. `update` reresuelve el arbol entero en cada
# construccion, reescribe el lock dentro de la imagen y hace que dos builds del mismo
# commit puedan llevar dependencias distintas; ademas desalinea el inventario de
# sbom.json, que se genera a partir del lock. Aqui importa especialmente porque el lock
# fija laravel/framework a 10.x-dev en un commit concreto: con `update` esa rama de
# desarrollo deriva sola. Si el lock no concuerda con composer.json, install falla, que
# es justo el aviso que se quiere.
# NOTA: el lock ya NO fija 10.x-dev. GDTIS-PT01-COD-099 se subsano pineando
# laravel/framework a v10.50.3 con minimum-stability: stable. El razonamiento de
# `install` frente a `update` sigue vigente: es lo que garantiza que la imagen
# lleve exactamente el arbol del lock versionado.
# `preferred-install: auto` en vez del `dist` de composer.json: sigue prefiriendo el zip
# de dist, pero cuando la descarga falla clona desde el repositorio en la misma referencia
# del lock, en lugar de abortar la construccion entera. Con `dist` a secas composer
# imprime «Source fallback is disabled. Not trying alternative sources.» y sale con 100.
#
# Hace falta porque GitHub rechaza intermitentemente su propio endpoint de archivo
# `codeload.github.com/<repo>/legacy.zip/<sha-de-40>` con un 400 —mientras `zip/<sha>` y
# `legacy.zip/<sha-corto>` responden 200—, y es exactamente la URL que construye composer
# al no haber token de GitHub. Sin esto, tres paquetes cualesquiera de los 98 tumban el
# build por algo que no esta ni en el lock ni en el codigo. La referencia instalada es la
# misma, asi que la construccion sigue siendo reproducible.
RUN composer config --no-plugins preferred-install auto \
    && composer install --no-dev --optimize-autoloader --no-interaction
