<?php

namespace App\Http\V1\Resources\OutConnectors;

class SimpleOutConnectorResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $data = [
            'id' => $this->id,
            'name' => $this->name,
            'type' => $this->type,
            'status' => $this->status,
            'user_id' => $this->user_id,
            'last_connection' => $this->last_connection,
            'retries' => (int) $this->retries,
        ];

        return $data;
    }
}
