<?php

namespace App\Http\V1\Resources\OutConnectors;

use App\Models\OutConnectors\MqttConnector;

class OutConnectorResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'type' => $this->type,
            'status' => $this->status,
            'user_id' => $this->user_id,
            'last_connection' => $this->last_connection,
            'use_readable_names' => (bool) $this->use_readable_names,
            'connector' => $this->connectorData(),
            'entities' => $this->whenLoaded('entities', fn () => $this->entities->map(
                fn ($entity) => ['id' => $entity->id, 'urn' => $entity->urn]
            )),
            'devices' => $this->whenLoaded('devices', fn () => $this->devices->map(
                fn ($device) => ['id' => $device->id, 'serial' => $device->serial, 'name' => $device->name]
            )),
            'created_at' => (string) $this->created_at,
            'updated_at' => (string) $this->updated_at,
        ];
    }

    private function connectorData(): ?array
    {
        $connector = $this->connectable;

        if (!$connector instanceof MqttConnector) {
            return null;
        }

        // The password never leaves the API: the client only learns whether one is set.
        return [
            'ipAddress' => $connector->ipAddress,
            'port' => $connector->port,
            'username' => $connector->username,
            'has_password' => !empty($connector->password),
            'clientId' => $connector->clientId,
            'ssl' => (bool) $connector->ssl,
            'sslCert' => $connector->sslCert,
            'topicTemplate' => $connector->topicTemplate,
            'payload_type' => $connector->payload_type,
            'payload_config' => $connector->payload_config,
        ];
    }
}
