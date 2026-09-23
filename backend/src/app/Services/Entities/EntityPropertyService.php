<?php

namespace App\Services\Entities;

use App\Helpers\AetherLinkHelper;
use App\Models\Device;
use App\Models\Entity;
use App\Models\Realtime\EntityProperty;
use Illuminate\Support\Facades\Log;

/**
 * The work behind updating an entity's properties, one rule per method. The controller
 * keeps the HTTP concerns: authorization, status codes and response shape.
 */
class EntityPropertyService
{
    /**
     * Turn the request payload into NGSI-LD attributes.
     *
     * A value already in NGSI-LD form (it carries `value` and `type`) is passed
     * through untouched, including its own timestamp; a plain value is wrapped and
     * only then does the payload's global timestamp apply.
     */
    public function toNgsiAttributes(array $payload): array
    {
        $timestamp = $payload['timestamp'] ?? null;
        unset($payload['timestamp']);

        $attributes = [];
        foreach ($payload as $name => $value) {
            if (is_array($value) && isset($value['value']) && isset($value['type'])) {
                $attributes[$name] = $value;
                continue;
            }

            $attributes[$name] = ['value' => $value, 'type' => 'Property'];
            if ($timestamp) {
                $attributes[$name]['timestamp'] = $timestamp;
            }
        }

        return $attributes;
    }

    /** Mirror each attribute's unitCode into the realtime property table. */
    public function persistUnits(Entity $entity, array $attributes): void
    {
        foreach ($attributes as $name => $data) {
            if (is_array($data) && isset($data['unitCode'])) {
                EntityProperty::where('entity_id', $entity->id)
                    ->where('name', $name)
                    ->update(['units' => $data['unitCode']]);
            }
        }
    }

    /**
     * Finds associated 'smsp_fiware' devices and sends commands to disable GPS and set new coordinates.
     *
     * @param Entity $entity The entity for which to find associated devices.
     * @param array $geolocationValue GeoJSON Point format: {"type": "Point", "coordinates": [lng, lat]}
     * @return bool Returns `true` if at least one command was sent, otherwise `false`.
     */
    public function handleSmartSpotLocationUpdate(Entity $entity, array $geolocationValue): bool
    {
        $smartSpotDevices = $this->getSmartSpotDevices($entity);
        if ($smartSpotDevices->isEmpty()) {
            return false;
        }

        $commandSent = false;
        foreach ($smartSpotDevices as $device) {
            if ($this->sendLocationCommandsToSmspFiwareDevice($device, $entity, $geolocationValue)) {
                $commandSent = true;
            }
        }

        return $commandSent;
    }

    /**
     * Get SmartSpot devices associated with an entity.
     */
    private function getSmartSpotDevices(Entity $entity)
    {
        return $entity->devices()->whereHas('deviceType', function ($query) {
            $query->where('code', 'smsp_fiware');
        })->get();
    }

    /**
     * Find entities from a device that have the rw_dho_upd_location command.
     */
    private function getEntitiesWithLocationCommand(Device $device)
    {
        $deviceEntities = $device->entities()->get();
        $entitiesWithCommand = $deviceEntities->filter(function ($entity) {
            return $entity->commands()->where('name', 'rw_dho_upd_location')->exists();
        });

        return $entitiesWithCommand;
    }

    /**
     * Send location commands to all entities of a device that have the command.
     * Falls back to main entity if no entity with the command is found.
     */
    private function sendLocationCommandsToSmspFiwareDevice(Device $device, Entity $sourceEntity, array $geolocationValue): bool
    {
        try {
            $entitiesWithCommand = $this->getEntitiesWithLocationCommand($device);
            $targetEntities = $entitiesWithCommand->isNotEmpty()
                ? $entitiesWithCommand
                : collect([$device->mainEntity->first()])->filter();

            if ($targetEntities->isEmpty()) {
                throw new \Illuminate\Database\Eloquent\ModelNotFoundException('No suitable entity found');
            }

            $payload = [
                "rw_dho_upd_location" => [
                    "type" => "Command",
                    "value" => false
                ],
                "rw_dho_latitude" => [
                    "type" => "Command",
                    "value" => (float) $geolocationValue['coordinates'][1]
                ],
                "rw_dho_longitude" => [
                    "type" => "Command",
                    "value" => (float) $geolocationValue['coordinates'][0]
                ]
            ];

            foreach ($targetEntities as $targetEntity) {
                AetherLinkHelper::updateOnContextBroker(
                    $targetEntity->urn,
                    $targetEntity->tenant,
                    $targetEntity->scope,
                    $payload
                );
            }

            return true;
        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            Log::error('Failed to send disable GPS commands for smsp_fiware device.', [
                'device_serial' => $device->serial,
                'entity_id' => $sourceEntity->id,
                'error_message' => $e->getMessage(),
            ]);
            return false;
        }
    }
}
