<?php

namespace App\Http\V1\Resources;

class FiwareTenantResource extends \App\Http\V1\Resources\DefaultPermissionsResource
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

        // check if scopes is loaded
        if ($this->relationLoaded('scopes')) {
            $base['scopes'] = FiwareScopeResource::collection($this->scopes);
        }

        return $base;
    }
}