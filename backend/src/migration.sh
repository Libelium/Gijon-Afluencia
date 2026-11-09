#!/bin/bash

DB_WAIT_ATTEMPTS=60
DB_WAIT_SECONDS=5

# After a node reboot this runs while PostgreSQL is still starting up.
wait_for_database() {
    local database="$1"

    for attempt in $(seq 1 "$DB_WAIT_ATTEMPTS"); do
        if php artisan db:monitor --databases="$database" > /dev/null 2>&1; then
            return 0
        fi
        echo "Waiting for database $database ($attempt/$DB_WAIT_ATTEMPTS)..."
        sleep "$DB_WAIT_SECONDS"
    done

    echo "Database $database is not reachable"
    return 1
}

# No rollback on failure: each migration runs in its own transaction, so a failed one leaves
# nothing half done, while rolling back the last batch dropped tables that were in use.
run_migration() {
    local database="$1"
    local path="$2"
    local name="$3"

    echo "Running $name migrations"
    wait_for_database "$database" || return 1
    if ! php artisan migrate --database="$database" --path="$path" --force; then
        echo "$name migrations failed"
        return 1
    fi
    echo "$name migrations completed successfully."
}

status=0
run_migration "pgsql_realtime" "database/migrations/realtime/" "realtime" || status=1
run_migration "pgsql" "database/migrations" "app" || status=1

# Now, run seeders. They cannot be roolled back, and they should always work and be retrocompatible
echo "Running seeders"
php artisan db:seed --class=DeviceTypesSeeder

php artisan app:update-custom-datamodels

php artisan db:seed --class=SyncSeeder
php artisan db:seed --class=SaasOrganizationsSeeder
php artisan db:seed --class=MqttUserSeeder
php artisan keycloak:sync-user-locales
echo "Seeders completed."

exit "$status"
