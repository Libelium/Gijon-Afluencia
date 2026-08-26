<?php

namespace App\Http\V1\Resources;

use App\Repositories\DeviceRepository;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;
use App\Http\V1\Resources\DeviceTypeResource;

class DeviceFullResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {

        $response = [
            "id" => $this->id,
            "case_id" => $this->case_id ?? null,
            "name" => $this->name,
            "serial" => $this->serial,
            "description" => $this->description,
            "is_subscribed" => $this->subscribed_until >= now(),
            "properties" => $this->properties,
            "subscribed_until" => $this->subscribed_until,
            "type" => new DeviceTypeResource($this->deviceType),
        ];

        if ($this->entities) {
            $response['entities'] = $this->entities->pluck('id')->toArray();
            $response['related_entities'] = EntityTemplateResource::collection($this->entities);
        }

        if ($this->mainEntity && $this->mainEntity->count() > 0) {
            $mainEntity = $this->mainEntity[0];
            $response['main_entity'] = (new EntityTemplateResource($mainEntity))->toArray($request);
            if ($mainEntity->pivot && isset($mainEntity->pivot->entity_type)) {
                $response['main_entity']['entity_type'] = $mainEntity->pivot->entity_type;
            }
        }


        return $response;
    }
}
