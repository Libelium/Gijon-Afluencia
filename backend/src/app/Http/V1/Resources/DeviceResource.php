<?php

namespace App\Http\V1\Resources;

use App\Repositories\DeviceRepository;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;
use App\Http\V1\Resources\DeviceTypeResource;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;

class DeviceResource extends \App\Http\V1\Resources\DefaultPermissionsResource
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
            'time_last_data' => $this->time_last_data,
            'organization' => $this->organization,
            'main_entity' => $this->when($this->relationLoaded('mainEntity'), function () {
                $mainEntity = $this->mainEntity->first();
                return $mainEntity ? (new EntityTemplateResource($mainEntity))->toArray(request()) : null;
            }, $this->when($this->main_entity_urn ?? null, [
                'id' => $this->main_entity_id ?? null,
                'urn' => $this->main_entity_urn ?? null,
                'datamodel' => $this->main_entity_datamodel ?? null,
                'scope' => $this->main_entity_scope ?? null,
                'tenant' => $this->main_entity_tenant ?? null,
                'geolocation' => $this->geolocation ? RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($this->geolocation) : null,
            ])),
        ];

        if ($this->relationLoaded('entities') && $this->entities->isNotEmpty()) {
            $response['entities'] = $this->entities->pluck('id')->toArray();

            $firstEntity = $this->entities->keyBy('id')[$this->mainEntity[0]->id];
            if ($firstEntity->relationLoaded('entityProperties')) {
                $response['entity_properties'] = $firstEntity->entityProperties->mapWithKeys(function ($property) {
                    return [$property['name'] => $property['value']];
                });
            }
        }

        if ($this->relationLoaded('mainEntity') && $this->mainEntity->count() > 0) {
            $mainEntity = $this->mainEntity[0];
            $response['main_entity'] = (new EntityResource($mainEntity))->toArray($request);
            if ($mainEntity->pivot && isset($mainEntity->pivot->entity_type)) {
                $response['main_entity']['entity_type'] = $mainEntity->pivot->entity_type;
            }
        }


        return $response;
    }
}
