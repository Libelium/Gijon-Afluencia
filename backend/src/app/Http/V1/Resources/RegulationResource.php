<?php

namespace App\Http\V1\Resources;

class RegulationResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $base = $this->content;

        $base["id"] = $this->id;
        $base["name"] = $this->name;
        $base["dataModel"] = $this->datamodel;

        return $base;
    }
}
