<?php

namespace App\Helpers;

use App\Helpers\AetherLinkHelper;
use App\Http\V1\Controllers\OrganizationController;
use App\Models\ProbeType;
use App\Models\DeviceType;
use App\Models\Organization;
use App\Repositories\PreferenceRepository;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Repositories\OrganizationRepository;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use App\Contracts\ServiceMapProviderInterface;


enum SmspDatamodels: string
{
    case AirQualityObserved = "aqo";
    case NoiseLevelObserved = "nlo";
    case CrowdFlowEvent = "cfe";
    case CrowdFlowObserved = "cfo";
    case CrowdSimulationEvent = "cse";
    case WeatherObserved = "wto";
    case Device = "dev";
    case DeviceHealthObserved = "dho";
    case Irrigation = "irr";

    /**
     * Creates an enum instance from a string value.
     *
     * @param string $value The string value (e.g., 'aqo').
     * @return self The corresponding enum case.
     * @throws Exception if the value is invalid.
     */
    static function fromValue(string $value): SmspDatamodels
    {
        return match ($value) {
            'aqo' => self::AirQualityObserved,
            'nlo' => self::NoiseLevelObserved,
            'cfe' => self::CrowdFlowEvent,
            'cfo' => self::CrowdFlowObserved,
            'cse' => self::CrowdSimulationEvent,
            'wto' => self::WeatherObserved,
            'dev' => self::Device,
            'dho' => self::DeviceHealthObserved,
            'irr' => self::Irrigation,
            default => throw new \Exception('Invalid permission value: ' . $value),
        };
    }
}

use Exception;

class ServiceProvisioningHelper
{
    /**
     * Compares local device/probe types with remote IOTA services and provisions the missing ones.
     *
     * @param FiwareTenant $tenant The FIWARE tenant to check.
     * @param FiwareScope $scope The FIWARE scope to check.
     * @param string|null $datamodel Optional NGSI-LD entity_type to filter services.
     * @return array An array containing collections of services that were provisioned.
     * @throws Exception Re-throws any exception for the caller to handle.
     */
    public static function getDevicesAndProbesAndProvision(FiwareTenant $tenant, FiwareScope $scope, ?string $datamodel = null): array
    {
        try {
            $devicesDatamodels = self::generateDevicesDatamodelsList();
            $probesDatamodels  = self::generateProbesDatamodelsList();

            $remoteIotaServices = AetherLinkHelper::getIotaServices($tenant->name, $scope->name, $datamodel);

            $existingApiKeyPrefixes = self::extractSmspApiKeyPrefixes(
                $datamodel === null
                    ? $remoteIotaServices
                    : AetherLinkHelper::getIotaServices($tenant->name, $scope->name)
            );

            $provisionPayloadDevices = self::buildProvisionPayload($devicesDatamodels, false, $existingApiKeyPrefixes);
            $provisionPayloadProbes  = self::buildProvisionPayload($probesDatamodels, true, $existingApiKeyPrefixes);

            $allDevices = data_get($provisionPayloadDevices, 'services', []);
            $allProbes  = data_get($provisionPayloadProbes, 'services', []);

            $devices = collect($allDevices);
            $probes  = collect($allProbes);
            $remote  = collect($remoteIotaServices);

            $extractLocalKey = function (array $s): string {
                $entity = strtolower($s['entity_type'] ?? '');
                $code   = strtolower(data_get($s, 'internal_attributes.device_type_code'));
                return $entity . '|' . $code;
            };

            $remoteCompositeKeys = $remote->flatMap(function ($s) {
                $entity = strtolower($s['entity_type'] ?? '');
                $codes  = collect(data_get($s, 'internal_attributes', []))
                    ->pluck('device_type_code')
                    ->map(fn($c) => strtolower($c))
                    ->filter();

                return $codes->isEmpty()
                    ? [$entity . '|']
                    : $codes->map(fn($c) => $entity . '|' . $c);
            })
                ->unique()
                ->values();

            $devicesToProvision = $devices->reject(function ($s) use ($remoteCompositeKeys, $extractLocalKey) {
                return $remoteCompositeKeys->contains($extractLocalKey($s));
            })->values();

            $probesToProvision = $probes->reject(function ($s) use ($remoteCompositeKeys, $extractLocalKey) {
                return $remoteCompositeKeys->contains($extractLocalKey($s));
            })->values();


            $services = array_merge(
                $devicesToProvision->toArray(),
                $probesToProvision->toArray()
            );

            $response = self::provisionServices(
                $tenant->name,
                $scope->name,
                ['services' => $services],
            );

            $allEntityTypes = $devices->merge($probes)
                ->pluck('entity_type')
                ->filter()
                ->unique()
                ->values()
                ->all();

            self::createDatamodelSubscriptions($scope, $allEntityTypes);

            return [
                'devicesToProvision' => $devicesToProvision,
                'probesToProvision'  => $probesToProvision
            ];
        } catch (\Throwable $e) {
            throw new Exception("Error getting IOTA services: " . $e->getMessage(), 0, $e);
        }
    }

    /**
     * Compares mapped services with remote IOTA services and provisions the missing entities.
     *
     * @param FiwareTenant $tenant The FIWARE tenant to check.
     * @param FiwareScope $scope The FIWARE scope to check.
     * @return array A list of entity types that were provisioned.
     */
    public static function getEntitiesToProvisionAndProvision(FiwareTenant $tenant, FiwareScope $scope): array
    {
        $allAetherServices = collect(
            AetherLinkHelper::getIotaServices($tenant->name, $scope->name, false)
        )
            ->pluck('entity_type')
            ->filter()
            ->map(fn($et) => strtolower($et))
            ->unique();

        $serviceMap = resolve(ServiceMapProviderInterface::class)->provide();
        $allServices = collect($serviceMap)
            ->flatMap(fn(array $services) => $services)
            ->unique();

        $entitiesToProvision = $allServices
            ->reject(
                fn(string $entity) =>
                $allAetherServices->contains(strtolower($entity))
            )
            ->values();


        self::provisionService($tenant->name, $scope->name, $entitiesToProvision->all());
        self::createDatamodelSubscriptions($scope, $allServices->values()->all());

        return $entitiesToProvision->all();
    }

    /**
     * Triggers the provisioning process for all organizations in the system.
     *
     * @return array A structured report of the provisioning results per organization.
     */
    public static function provisionAllOrganizations(): array
    {
        Organization::with(['adminUser'])->chunk(50, function ($orgs) use (&$result) {
            $result = [];
            foreach ($orgs as $org) {
                try {
                    $mainScopePreference = 'mainScope';
                    $mainScopeId = PreferenceRepository::getOrganizationPreference($org, $mainScopePreference);
                    if (!$mainScopeId) {
                        $result[$org->id] = ['error' => "No {$mainScopePreference} preference found."];
                        continue;
                    }

                    $mainScope = FiwareScope::with('tenant')->find($mainScopeId);
                    if (!$mainScope || !$mainScope->tenant) {
                        $result[$org->id] = ['error' => 'mainScope or its tenant not found'];
                        continue;
                    }
                    $diff = self::getDevicesAndProbesAndProvision($mainScope->tenant, $mainScope);

                    $dataScopePreference = 'platformDataScope';
                    $dataScopeId = PreferenceRepository::getOrganizationPreference($org, $dataScopePreference);
                    if (!$dataScopeId) {
                        $result[$org->id] = ['error' => "No {$dataScopePreference} preference found."];
                        continue;
                    }

                    $dataScope = FiwareScope::with('tenant')->find($dataScopeId);
                    if (!$dataScope || !$dataScope->tenant) {
                        $result[$org->id] = ['error' => 'platformDataScope or its tenant not found'];
                        continue;
                    }
                    $entitiesToProvision = self::getEntitiesToProvisionAndProvision($dataScope->tenant, $dataScope);

                    $result[$org->id] = [
                        'organization'        => $org->name,
                        'devicesToProvision'  => $diff['devicesToProvision'],
                        'probesToProvision'   => $diff['probesToProvision'],
                        'entitiesToProvision' => $entitiesToProvision,
                    ];
                } catch (\Throwable $e) {
                    $result[$org->id] = ['error' => $e->getMessage()];
                }
            }
        });

        return $result;
    }

    /**
     * Provisions the main services (devices and probes) for a specific organization.
     *
     * @param Organization $org The organization to provision services for.
     * @return void
     */
    public static function provisionMainServices(Organization $org): void
    {
        $scope = OrganizationRepository::getOrganizationScope($org, 'mainScope');

        $devicesDatamodels = self::generateDevicesDatamodelsList();
        self::provisionService($scope->tenant->name, $scope->name, $devicesDatamodels);

        $probesDatamodels = self::generateProbesDatamodelsList();
        self::provisionService($scope->tenant->name, $scope->name, $probesDatamodels, true);
    }

    /**
     * Provisions the main services (devices and probes) on an explicit scope and
     * subscribes it to the main datamodels. Unlike provisionMainServices, this
     * does not look the scope up by organization preference, which makes it
     * suitable for additional (slug based) tenants.
     *
     * @param FiwareScope $scope The scope to provision and subscribe.
     * @return void
     */
    public static function provisionMainServicesForScope(FiwareScope $scope): void
    {
        $scope->loadMissing('tenant');

        $devicesDatamodels = self::generateDevicesDatamodelsList();
        self::provisionService($scope->tenant->name, $scope->name, $devicesDatamodels);

        $probesDatamodels = self::generateProbesDatamodelsList();
        self::provisionService($scope->tenant->name, $scope->name, $probesDatamodels, true);

        $datamodels = array_values(self::generateDatamodelsList());
        self::createDatamodelSubscriptions($scope, $datamodels);
    }

    /**
     * Generates a combined list of datamodels for all devices and probes.
     *
     * @return array A map of [code => datamodel].
     */
    public static function generateDatamodelsList(): array
    {
        $devicesDatamodels = self::generateDevicesDatamodelsList();
        $probesDatamodels = self::generateProbesDatamodelsList();
        return array_filter(array_merge($devicesDatamodels, $probesDatamodels));
    }

    /**
     * Generates a list of datamodels for all device types in the database.
     *
     * @return array A map of [code => datamodel].
     */
    private static function generateDevicesDatamodelsList(): array
    {
        return DeviceType::all()->flatMap(function ($device) {
            $result = [];

            if (!$device->fiware_properties) {
                return $result;
            }

            if (isset($device->fiware_properties['extra_datamodels'])) {
                foreach ($device->fiware_properties['extra_datamodels'] as $datamodel) {
                    $result[$device->code . '_' . $datamodel['value']] = $datamodel['datamodel'];
                }
            } else {
                $result[$device->code] = $device->fiware_properties['default_datamodel'] ?? null;
            }

            return $result;
        })->toArray();
    }

    /**
     * Generates a list of datamodels for all probe types in the database.
     *
     * @return array A map of [code => datamodel].
     */
    private static function generateProbesDatamodelsList(): array
    {
        return ProbeType::all()->mapWithKeys(function ($probe) {
            return [$probe->code => $probe->fiware_properties['default_datamodel'] ?? $probe->name];
        })->toArray();
    }

    /**
     * Builds the provisioning payload and sends it to the provisioning endpoint.
     *
     * @param string $tenant The FIWARE tenant name.
     * @param string $scope The FIWARE scope name.
     * @param array $datamodels A map of [code => datamodel] to provision.
     * @param bool $provisionAttributes Whether to include static attributes in the payload.
     * @return mixed The response from the provisioning service.
     */
    public static function provisionService(string $tenant, string $scope, array $datamodels, bool $provisionAttributes = false)
    {
        $services = self::buildProvisionPayload($datamodels, $provisionAttributes);
        return AetherLinkHelper::provisionService($tenant, $scope, $services);
    }

    /**
     * Provisions services with attribute mappings.
     *
     * @param string $tenant The FIWARE tenant name.
     * @param string $scope The FIWARE scope name.
     * @param array $datamodels A map of [code => datamodel].
     * @param array $attributeMappings Array of attribute mappings with sourceAttribute, targetAttribute, type.
     * @return mixed The response from the provisioning service.
     */
    public static function provisionServiceWithMappings(string $tenant, string $scope, array $datamodels, array $attributeMappings = [])
    {
        $services = self::buildProvisionPayload($datamodels, false);

        // Add attribute mappings to all services
        if (!empty($attributeMappings) && isset($services['services'])) {
            $attributes = [];
            foreach ($attributeMappings as $mapping) {
                $attributes[] = [
                    'object_id' => $mapping['sourceAttribute'],
                    'name' => $mapping['targetAttribute'],
                    'type' => $mapping['type'],
                ];
            }

            foreach ($services['services'] as &$service) {
                $service['attributes'] = $attributes;
            }
        }

        return AetherLinkHelper::provisionService($tenant, $scope, $services);
    }

    /**
     * A wrapper to send a pre-built services payload to the provisioning endpoint.
     *
     * @param string $tenant The FIWARE tenant name.
     * @param string $scope The FIWARE scope name.
     * @param array $services The services payload.
     * @return mixed The response from the provisioning service.
     */
    public static function provisionServices(string $tenant, string $scope, array $services)
    {
        return AetherLinkHelper::provisionService($tenant, $scope, $services);
    }

    /**
     * Extracts the shared apikey prefix of each smsp family already provisioned
     * in the IOTA. Smart Spot firmware posts with <family prefix> + 3-letter
     * datamodel suffix, so every service of a family must share one prefix:
     * when provisioning incrementally, reuse the remote prefix instead of
     * generating a new random one.
     *
     * @param array $remoteIotaServices Services already provisioned in the IOTA.
     * @return array A map of [collapsed smsp code => apikey prefix].
     */
    private static function extractSmspApiKeyPrefixes(array $remoteIotaServices): array
    {
        $prefixes = [];

        foreach ($remoteIotaServices as $service) {
            $apikey = $service['apikey'] ?? null;
            if (!$apikey) {
                continue;
            }

            $codes = collect(data_get($service, 'internal_attributes') ?? [])
                ->pluck('device_type_code')
                ->filter();

            foreach ($codes as $serviceCode) {
                if (str_contains($serviceCode, 'smsp_fiware')) {
                    $prefixes['smsp_fiware'] ??= substr($apikey, 0, -3);
                } elseif (str_contains($serviceCode, 'smsp')) {
                    $prefixes['smsp'] ??= substr($apikey, 0, -3);
                }
            }
        }

        return $prefixes;
    }

    /**
     * Builds the final service payload array for the IOTA provisioning API.
     *
     * @param array $datamodels A map of [code => datamodel].
     * @param bool $provisionAttributes Whether to include static attributes.
     * @param array $existingApiKeys A map of [code => apikey prefix] to reuse instead of generating new ones.
     * @return array The structured payload.
     */
    private static function buildProvisionPayload(array $datamodels, bool $provisionAttributes, array $existingApiKeys = []): array
    {
        // Store API keys for unique codes
        $apiKeys = [];
        $services = [];

        foreach ($datamodels as $code => $datamodel) {
            // Exceptional if condition to smsp
            if (str_contains($code, 'smsp_fiware')) {
                $code = 'smsp_fiware';
            } else  if (str_contains($code, 'smsp')) {
                $code = 'smsp';
            }

            if (!isset($apiKeys[$code]))
                $apiKeys[$code] = $existingApiKeys[$code] ?? bin2hex(random_bytes(8));

            $apiKey = str_contains($code, 'smsp') ?  $apiKeys[$code]  . constant(SmspDatamodels::class . "::$datamodel")->value : $apiKeys[$code];



            $services[] = self::buildService($code, $datamodel, $apiKey, $provisionAttributes);
        }

        return ['services' => $services];
    }


    /**
     * Builds the array structure for a single service.
     *
     * @param string $code The original device/probe code.
     * @param string $datamodel The entity type for the service.
     * @param string $apikey The generated API key.
     * @param bool $provisionAttributes Whether to include static attributes.
     * @return array The service array.
     */
    private static function buildService(string $code, string $datamodel, string $apikey, bool $provisionAttributes): array
    {

        if ($provisionAttributes) {
            $probeType = ProbeType::where('code', $code)->first();
            $attributes = FiwareProvisioningHelper::buildAttributesPayload($probeType->id, get_class($probeType), $datamodel);
        }
        return [
            'apikey' => $apikey,
            'entity_type' => $datamodel,
            'resource' => '/iot/json',
            'transport' => 'HTTP',
            'internal_attributes' => ['device_type_code' => $code],
            'attributes' => $attributes ?? [],
        ];
    }

    /**
     * This creates the datamodel subscriptions for the organization, with the given $datamodels.
     * 
     * @param \App\Models\Organization $organization
     * @param array $datamodels
     * 
     * @return void
     * 
     * @throws Exception if the request to the queues service fails.
     */
    public static function createDatamodelSubscriptions(FiwareScope $scope, array $datamodels): void
    {
        if (empty($datamodels)) {
            return;
        }

        $scope->loadmissing('tenant');

        $queuesService = config('services.queues-consumer.publish');
        $message = [
            'task' => 'platform.sync.fiware_type_subscription_job',
            'params' => [
                "subscribe_types" => $datamodels,
                "tenant" => $scope->tenant->name,
                "scope" => $scope->name,
                "unsubscribe_types" => [],
                "auto_discovery" => false,
            ],
        ];

        $response = Http::post($queuesService, $message);

        if ($response->status() >= 400) {
            throw new \Exception("Error creating subscriptions for tenant "
                . $scope->tenant->name . " and scope " . $scope->name);
        }

        Log::info("Subscribed to datamodels successfully", [
            'tenant' => $scope->tenant->name,
            'scope' => $scope->name,
            'datamodels' => $datamodels,
            'response_status' => $response->status(),
        ]);
    }

    /**
     * Orchestrates the complete provisioning and subscription process for a new organization.
     *
     * @param Organization $organization The organization to set up.
     * @param FiwareScope $mainScope The organization's main scope.
     * @param FiwareScope $dataScope The organization's specialized data scope.
     * @return void
     */
    public static function provisionAndSubscribe(Organization $organization, FiwareScope $mainScope, FiwareScope $dataScope): void
    {
        self::provisionMainServices($organization);
        $services = self::generateDatamodelsList();

        $datamodels = array_values($services);
        self::createDatamodelSubscriptions($mainScope, $datamodels);
        self::provisionDataScopeServices($organization);

        $serviceMap = resolve(ServiceMapProviderInterface::class)->provide();
        $allDatamodels = array_merge(...array_values($serviceMap));
        self::createDatamodelSubscriptions($dataScope, $allDatamodels);
    }

    /**
     * Provisions all services defined in the service map for the platformDataScope.
     * This method replaces the individual provision...Service methods.
     *
     * @param Organization $organization The organization to provision services for.
     * @return void
     */
    private static function provisionDataScopeServices(Organization $organization): void
    {
        $scope = OrganizationRepository::getOrganizationScope($organization, 'platformDataScope');

        if (!$scope || !$scope->tenant) {
            return;
        }
        $serviceMap = resolve(ServiceMapProviderInterface::class)->provide();
        $datamodels = array_merge(...array_values($serviceMap));
        self::provisionService($scope->tenant->name, $scope->name, $datamodels);
    }
}
