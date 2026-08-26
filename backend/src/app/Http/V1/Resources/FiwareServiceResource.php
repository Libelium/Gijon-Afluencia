<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class FiwareServiceResource extends JsonResource
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
            'tenant' => $this["service"],
            'scope' => $this["subservice"],
            'apikey' => $this["apikey"],
            'entity_type' => $this["entity_type"],
            'device_type' => $this["internal_attributes"][0]['device_type_code'] ?? null,
            'attributes' => $this["attributes"] ?? [],
        ];
    }
}
