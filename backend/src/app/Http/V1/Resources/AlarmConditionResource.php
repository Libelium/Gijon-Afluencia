<?php

namespace App\Http\V1\Resources;

use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use Illuminate\Http\Resources\Json\JsonResource;

class AlarmConditionResource extends JsonResource
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
            'alarmId' => (int) $this->alarm_id,
            'entity' => EntityResource::make($this->entity),
            'measure' => (array) [
                'id' => (string) $this->measure,
                'name' => (string) RealtimeEntityResourcesHelper::camelCaseToSpaced($this->measure),
            ],
            'condition' => (string) $this->condition,
            'threshold' => (array) $this->threshold,
            'period' => (array) $this->period,
        ];
    }
}
