<?php

namespace App\Http\V1\Resources;

class FiwareScopeResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $base = [
            'id' => $this->id,
            'name' => $this->name,
        ];

        // check if tenants relation is loaded
        if ($this->relationLoaded('tenant')) {
            $base['tenant'] = new FiwareTenantResource($this->tenant);
        }

        return $base;
    }
}