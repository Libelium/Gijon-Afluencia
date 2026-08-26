<?php

namespace App\Http\V1\Resources;

use App\Http\V1\Resources\Realtime\EntityPropertyResource;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class EntityTemplateResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $splitted_urn = explode(':', $this->urn);

        $aux_name = $splitted_urn[count($splitted_urn) - 1];

        $response = [
            'id' => $this->id,
            'name' => $aux_name,
            'urn' => $this->urn,
            'datamodel' => $this->datamodel,
            'scope' => isset($this->fiwareScope) ? $this->fiwareScope->name : null,
            'scope_id' => isset($this->fiwareScope) ? $this->fiwareScope->id : null,
            'tenant' => isset($this->fiwareScope) && isset($this->fiwareScope->tenant) ? $this->fiwareScope->tenant->name : null,
            'tenant_id' => isset($this->fiwareScope) && isset($this->fiwareScope->tenant) ? $this->fiwareScope->tenant->id : null,
        ];

        if ($this->entityProperties) {
            $response['properties'] = EntityPropertyResource::collection($this->entityProperties);
        }

        if ($this->devices){
            $response['devices'] = $this->devices->pluck('id')->toArray();
        }

        if ($this->geolocation) {
            $response['geolocation'] = (new EntityPropertyResource($this->geolocation))->toArray($request)['value'];
        }

        if ($this->name) {
            $response['name'] = (new EntityPropertyResource($this->name))->toArray($request)['value'];
        }

        return $response;
    }
}
