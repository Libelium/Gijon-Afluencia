<?php

namespace App\Http\V1\Resources;

class AlarmResource extends \App\Http\V1\Resources\DefaultPermissionsResource
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
            'id' => (int) $this->id,
            'userId' => (int) $this->user_id,
            'name' => (string) $this->name,
            'type' => (string) $this->type,
            'function' => (string) $this->function,
            'up' => (bool) $this->up,
            'disabled' => (bool) $this->disabled,
            'conditions' => isset($this->conditions) ? AlarmConditionResource::collection($this->conditions) : null,
            'inactivityConditions' => isset($this->inactivityConditions) ? InactivityAlarmConditionResource::collection($this->inactivityConditions) : null,
            'createdAt' => (string) $this->created_at,
            'updatedAt' => (string) $this->updated_at,
        ];
    }
}
