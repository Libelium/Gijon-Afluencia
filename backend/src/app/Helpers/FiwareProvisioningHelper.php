<?php

namespace App\Helpers;

use Illuminate\Support\Str;

use App\Exceptions\EntityAlreadyExistException;
use App\Models\CustomDatamodel;
use App\Models\Device;
use App\Models\DeviceType;
use App\Models\FiwareScope;
use App\Helpers\AetherLinkHelper;
use App\Models\Entity;

class FiwareProvisioningHelper
{

    public static function provisionDeviceWithNewEntity(
        Device $device,
        FiwareScope $scope,
        ?string $entityName
    ): Entity {

        $fiware_props = $device->deviceType->fiware_properties;
        if (!array_key_exists('default_datamodel', $fiware_props)) {
            throw new \Exception("No default datamodel defined for the given device type");
        }

        $defaultDatamodel = $device->deviceType->fiware_properties['default_datamodel'];
        if (!$defaultDatamodel) {
            throw new \Exception("No default datamodel defined for the given device type "
                . $device->deviceType->name);
        }

        if ($entityName) {
            $entityUrn = 'urn:ngsi-ld:' . $defaultDatamodel . ':' . $entityName;
            if (Entity::where('urn', $entityUrn)->where('fiware_scope_id', $scope->id)->exists()) {
                $entityName = null;
            }
        }

        if (!$entityName) {
            $entityName = self::buildEntityName($device);
        }

        $entity = self::createEntity($entityName, $defaultDatamodel, $scope);

        try {
            self::provisionDeviceForEntity($device, $entity);
            AetherLinkHelper::createContextBrokerEntity(
                $scope->tenant->name,
                $scope->name,
                [
                    [
                        "id" => $entity->urn,
                        "type" => $defaultDatamodel,
                        "attributes" => [
                            "name" => [
                                "type" => "Property",
                                "value" => $device->name ?? $device->serial,
                            ],
                        ]
                    ]
                ]
            );
        } catch (\Exception $e) {
            $entity->delete();
            throw $e;
        }

        $device->entities()->sync([$entity->id => ['entity_type' => 'main']]);

        return $entity;
    }

    private static function buildEntityName(Device $device): string
    {
        // check if it has main entity
        $mainEntity = $device->entities()->wherePivot('entity_type', 'main')->first();

        if (!$mainEntity) {
            $defaultDatamodel = $device->deviceType->fiware_properties['default_datamodel'];
            return $defaultDatamodel . '_' . $device->id;
        }

        $urnParts = explode(':', $mainEntity->urn);
        return end($urnParts);
    }

    public static function provisionDeviceForEntity(Device $device, Entity $entity): array
    {
        $provisionPayload = self::buildProvisioningPayload($device, $entity);

        $response = AetherLinkHelper::provisionDevice(
            $provisionPayload['service']['service'],
            $provisionPayload['service']['subservice'],
            $provisionPayload['payload']
        );

        if ($response->status() != 200) {
            response()->json([
                'message' => 'Error provisioning device in Fiware',
                'status' => $response->status(),
                'body' => $response->body(),
            ], 500)->throwResponse();
        }

        return $provisionPayload;
    }

    private static function createEntity(
        string $entityName,
        string $datamodel,
        FiwareScope $scope
    ): Entity {

        $entityUrn = 'urn:ngsi-ld:' . $datamodel . ':' . $entityName;

        $entity = Entity::where('urn', $entityUrn)
            ->where('fiware_scope_id', $scope->id)
            ->first();

        if ($entity) {
            throw new EntityAlreadyExistException("Entity with urn " . $entityUrn .
                " already exists in scope: (" . $scope->tenant->name . ", " . $scope->name . ")");
        }

        return Entity::create([
            'urn' => $entityUrn,
            'datamodel' => $datamodel,
            'fiware_scope_id' => $scope->id,
            'tenant' => $scope->tenant->name,
            'scope' => $scope->name,
        ]);
    }

    private static function getDeviceIotaService(DeviceType $deviceType, FiwareScope $scope, string $datamodel): array
    {
        $services = AetherLinkHelper::getIotaServices(
            $scope->tenant->name,
            $scope->name,
            $datamodel
        );

        if (!$services) {
            return [];
        }

        $deviceService = array_filter($services, function ($service) use ($deviceType) {
            if (!isset($service['internal_attributes'][0]['device_type_code'])) {
                return false;
            }
            return $service['internal_attributes'][0]['device_type_code'] == $deviceType->code;
        });

        return reset($deviceService) ?? [];
    }

    private static function buildExtraDatamodelsPayload(Device $device, Entity $mainEntity): array
    {
        $extraDatamodels = $device->deviceType->fiware_properties['extra_datamodels'] ?? [];
        $protocol = $device->deviceType->fiware_properties['protocol'] ?? "HTTP";

        $fwDevices = [];
        foreach ($extraDatamodels as $extra) {
            if ($mainEntity->datamodel == $extra['datamodel']) {
                continue;
            }

            $service = self::getDeviceIotaService($device->deviceType, $mainEntity->fiwareScope, $extra['datamodel']);
            $device_id = $device->serial . '_' . strtoupper($extra['value']);
            $payload = [
                'device_id' => $device_id,
                "entity_name" => 'urn:ngsi-ld:' . $extra['datamodel'] . ':' . $device_id,
                "entity_type" => $extra['datamodel'],
                'apikey' => $service["apikey"],
                "transport" => $protocol,
            ];

            $deviceType = $device->deviceType;
            $attributesPayload = self::buildAttributesPayload($deviceType->id, get_class($deviceType), $extra['datamodel']);

            if ($attributesPayload) {
                $payload['attributes'] = $attributesPayload;
            }

            $commandsPayload = self::buildCommandsProvisioningPayload($device, $device_id, $extra['datamodel']);

            # merge because commands generates "commands" and "static_attributes" keys
            if ($commandsPayload) {
                $payload = array_merge($payload, $commandsPayload);
            }

            $fwDevices[] = $payload;
        }

        return $fwDevices;
    }

    private static function buildMainEntityPayload(Device $device, Entity $entity, string $apikey)
    {
        $deviceId = self::getDeviceId($device);
        $payload = [
            'device_id' => $deviceId,
            "entity_name" => $entity->urn,
            "entity_type" => $entity->datamodel,
            'apikey' => $apikey,
            "transport" => $device->deviceType->fiware_properties['protocol'] ?? "HTTP",
        ];

        $deviceType = $device->deviceType;
        $attributesPayload = self::buildAttributesPayload($deviceType->id, get_class($deviceType), $entity->datamodel);

        if ($attributesPayload) {
            $payload['attributes'] = $attributesPayload;
        }

        $commandsPayload = self::buildCommandsProvisioningPayload($device, $deviceId, $entity->datamodel);

        # merge because commands generates "commands" and "static_attributes" keys
        if ($commandsPayload) {
            $payload = array_merge($payload, $commandsPayload);
        }

        return $payload;
    }

    private static function getDeviceId(Device $device)
    {
        if (Str::contains($device->deviceType->code, 'smsp')) {
            return $device->serial . "_DEV";
        }

        return strtoupper($device->serial);
    }

    private static function buildProvisioningPayload(Device $device, Entity $entity): array
    {

        if (!isset($device->deviceType->fiware_properties['default_datamodel'])) {
            throw new \Exception("No default datamodel defined for the given device type");
        }

        $service = self::getDeviceIotaService($device->deviceType, $entity->fiwareScope, $entity->datamodel);

        if (!$service) {
            throw new \Exception("No services available for the given tenant, scope and datamodel");
        }

        if (!isset($service["apikey"])) {
            throw new \Exception("No apikey available for the given service");
        }

        $apikey = $service["apikey"];
        $mainEntity = self::buildMainEntityPayload($device, $entity, $apikey);
        $fwDevices = self::buildExtraDatamodelsPayload($device, $entity);

        return ['service' => $service, 'payload' => ['devices' => array_merge([$mainEntity], $fwDevices)]];
    }

    public static function buildAttributesPayload(int $resourceId, string $resourceType, string $datamodel): array
    {

        if ($resourceType == 'devices' && $resourceId == '3') {
            // Legacy one case
            return self::buildOneAttributesPayload();
        }

        $attrs = CustomDatamodel::select('custom_datamodels.command', 'custom_datamodels.units', 'custom_datamodel_mappings.mapping')
            ->join('custom_datamodel_mappings', 'custom_datamodels.id', '=', 'custom_datamodel_mappings.custom_datamodel_id')
            ->where('custom_datamodels.resource_id', $resourceId)
            ->where('custom_datamodels.resource_type', $resourceType)
            ->where('custom_datamodels.internal', false)
            ->where('custom_datamodel_mappings.datamodel', '=', $datamodel)
            ->get();

        if (!$attrs) {
            return [];
        }

        $payload = [];

        foreach ($attrs as $attr) {
            $attrId = $attr->command;
            $attrUnits = $attr->units;
            $attrName = $attr->mapping ?? $attrId;

            $attrPayload = [
                'object_id' => $attrId,
                'name' => $attrName,
                'type' => 'Property',
            ];

            if ($attrUnits && $attrUnits != CustomDatamodel::$DIMENSIONLESS_UNIT) {
                $attrPayload['metadata'] = [
                    'unitCode' => [
                        "type" => "Text",
                        "value" => $attrUnits,
                    ]
                ];
            }

            $payload[] = $attrPayload;
        }

        return $payload;
    }

    private static function buildOneAttributesPayload(): array
    {
        return [
            [
                'object_id' => 'socketAProbeRef',
                'name' => 'socketAProbeRef',
                'type' => 'Relationship',
            ],
            [
                'object_id' => 'socketBProbeRef',
                'name' => 'socketBProbeRef',
                'type' => 'Relationship',
            ],
            [
                'object_id' => 'socketCProbeRef',
                'name' => 'socketCProbeRef',
                'type' => 'Relationship',
            ],
            [
                'object_id' => 'socketDProbeRef',
                'name' => 'socketDProbeRef',
                'type' => 'Relationship',
            ],
        ];
    }

    /* This function builds the payload for commands provisioning
    * It retrieves commands from CustomDatamodel based on the device type and datamodel
    * It returns an array with the endpoint and commands to be provisioned
    * If no commands are found, it returns an empty array
    */
    private static function buildCommandsProvisioningPayload(Device $device, string $device_id, string|null $datamodel = null): array
    {

        $commands = self::getCommands($device, $datamodel);
        if (!$commands) {
            return [];
        }

        $payload = [];

        $payload['endpoint'] = self::buildCommandEndpoint($device, $device_id);

        $payload['commands'] = $commands->map(function ($command) {
            return [
                'name' => $command->command,
                'type' => "Property",
            ];
        });

        $payload['static_attributes'] = [
            [
                'name' => 'commands',
                'type' => 'Property',
                'value' => $commands->map(function ($command) {
                    return $command->command;
                }),
            ],
        ];

        return $payload;
    }

    /* Builds the IoT Agent endpoint that delivers commands to the device.
     * Smart Parking V2 ('parking') is a LoRaWAN device: its commands must be sent
     * as LoRaWAN downlinks, not pushed through the generic HTTP command route.
     */
    private static function buildCommandEndpoint(Device $device, string $device_id): string
    {
        $path = $device->deviceType->code === 'parking'
            ? '/lorawan/downlink/'
            : '/notify/command/';

        return env('COMMANDS_ENDPOINT') . $path . $device_id;
    }

    public static function getCommands(Device $device, string|null $datamodel = null)
    {
        $query = CustomDatamodel::where('resource_id', $device->device_type_id)
            ->where('resource_type', DeviceType::class)
            ->whereIn('operations', ['rw', 'w']);

        if ($device->deviceType->code === 'smsp_fiware') {
            $query = $query->with(['customDatamodelMappings' => function ($query) use ($datamodel) {
                if ($datamodel !== null) {
                    $query->where('datamodel', $datamodel);
                }
            }])
                ->when($datamodel !== null, function ($query) use ($datamodel) {
                    return $query->whereHas('customDatamodelMappings', function ($q) use ($datamodel) {
                        $q->where('datamodel', $datamodel);
                    });
                });
        }

        return $query->get();
    }
}
