#!/bin/bash

run_migration() {
    local database="$1"
    local path="$2"
    local name="$3"

    echo "Running $name migrations"
    if ! php artisan migrate --database="$database" --path="$path" --force; then
        echo "$name migrations failed, rolling back..."
        php artisan migrate:rollback --database="$database" --path="$path" --force
    else
        echo "$name migrations completed successfully."
    fi
}

run_migration "device_manager" "database/migrations/device_manager" "Bootstrap"
run_migration "pgsql_realtime" "database/migrations/realtime/" "realtime"
run_migration "pgsql" "database/migrations" "app"

# Now, run seeders. They cannot be roolled back, and they should always work and be retrocompatible
echo "Running seeders"
php artisan db:seed --class=DeviceTypesSeeder

php artisan app:update-custom-datamodels

php artisan db:seed --class=SyncSeeder
php artisan db:seed --class=SaasOrganizationsSeeder
php artisan db:seed --class=MqttUserSeeder
php artisan keycloak:sync-user-locales
echo "Seeders completed."