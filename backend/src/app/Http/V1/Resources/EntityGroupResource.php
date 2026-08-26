<?php

namespace App\Http\V1\Resources;

class EntityGroupResource extends DefaultPermissionsResource
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
            "id"             => $this->id,
            "type"           => $this->type,
            "name"           => $this->name,
            "description"    => $this->description,
            "user_id"        => $this->user_id,
            "max_capacity"   => $this->max_capacity,
            "total_area"     => $this->total_area,
            "linked_entity"  => $this->linkedEntity ? new EntityResource($this->linkedEntity) : null,
            "entities"       => isset($this->entities) ? EntityResource::collection($this->entities) : [],
        ];
    }
}
