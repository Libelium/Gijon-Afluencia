<?php

namespace App\Providers;

use Illuminate\Database\Eloquent\Relations\Relation;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use App\Authorization\ResourcePermissionCache;
use App\Contracts\ServiceMapProviderInterface;
use App\Helpers\StaticServiceMapProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        if ($this->app->environment('local') && config('logging.queries') == 1) {
            DB::listen(function ($query) {
                $dateNow = date('Y-m-d');
                File::append(
                    storage_path('/logs/query-' . $dateNow . '.log'),
                    $query->sql . ' [' . implode(', ', $query->bindings) . ']' . PHP_EOL
                );
            });
        }

        $this->app->singleton(ResourcePermissionCache::class, ResourcePermissionCache::class);
        $this->app->bind(ServiceMapProviderInterface::class, StaticServiceMapProvider::class);
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        Relation::morphMap([
            'dashboards' => 'App\Models\Dashboard',
            'action_email' => 'App\Models\Actions\ActionEmail',
            'action_http_push' => 'App\Models\Actions\ActionHttpPush',
            'action_telegram' => 'App\Models\Actions\ActionTelegram',
            'action_whatsapp' => 'App\Models\Actions\ActionWhatsapp',
            'action_sms'      => 'App\Models\Actions\ActionSms',
            'action_entity_command' => 'App\Models\Actions\ActionEntityCommand',
            'http_connector' => 'App\Models\OutConnectors\HttpConnector',
            'mqtt_connector' => 'App\Models\OutConnectors\MqttConnector',
            'azureiot_connector' => 'App\Models\OutConnectors\AzureIotConnector',
            'loriot_connector' => 'App\Models\LoriotConnector',
            'sentilo_out_connector' => 'App\Models\OutConnectors\SentiloOutConnector',
            'fiware_out_connector' => 'App\Models\OutConnectors\FiwareOutConnector',
            'entities' => 'App\Models\Entity',
            'devices' => 'App\Models\Device',
            'alarms' => 'App\Models\Alarm',
            'out_connectors' => 'App\Models\OutConnectors\OutConnector',
            'in_connectors' => 'App\Models\InConnector',
            'fiware_scopes' => 'App\Models\FiwareScope',
            'fiware_tenants' => 'App\Models\FiwareTenant',
            'mapping_schemas' => 'App\Models\OutConnectors\MappingSchema',
        ]);
    }
}
