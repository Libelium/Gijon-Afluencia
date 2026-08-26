FROM php:8.2-apache-bookworm
# OFFICIAL IMAGE FROM https://hub.docker.com/_/php/

# User and Groups ID for mapping directories
ARG UID=1001
ARG GID=1001
ARG WITH_XDEBUG=false

# Use the default production configuration
COPY php.ini $PHP_INI_DIR/conf.d/

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
    libpng-dev \
    libjpeg-dev \
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
COPY apache2-laravel.conf /etc/apache2/sites-available/laravel.conf

# Apache rewrite + security headers
RUN a2dissite 000-default.conf && a2ensite laravel.conf && a2enmod rewrite && a2enmod headers

COPY --chown=www-data:www-data ./src /var/www/html
COPY --chmod=755 --chown=www-data:www-data ./src/migration.sh /var/www/html/migration.sh
COPY --chown=www-data:www-data ./libelium_devices_fiware_datamodels/*.csv /var/www/html/storage/app/CSV/devices/
COPY --chown=www-data:www-data ./libelium_devices_fiware_datamodels/one_sensor_datamodel.csv /var/www/html/storage/app/CSV/probes/

RUN rm /var/www/html/storage/app/CSV/devices/*sensor*

WORKDIR /var/www/html

EXPOSE 80

# compile app and serve for production

USER www-data

# `install` y NUNCA `update`: install resuelve desde el composer.lock versionado,
# que viaja en el COPY ./src de arriba. `update` reresuelve el arbol entero en cada
# construccion, reescribe el lock dentro de la imagen y hace que dos builds del mismo
# commit puedan llevar dependencias distintas; ademas desalinea el inventario de
# sbom.json, que se genera a partir del lock. Aqui importa especialmente porque el lock
# fija laravel/framework a 10.x-dev en un commit concreto: con `update` esa rama de
# desarrollo deriva sola. Si el lock no concuerda con composer.json, install falla, que
# es justo el aviso que se quiere.
RUN composer install --no-dev --optimize-autoloader --no-interaction

USER root
