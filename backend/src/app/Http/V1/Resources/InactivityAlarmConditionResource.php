<?php

namespace App\Http\V1\Resources;

use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use Illuminate\Http\Resources\Json\JsonResource;
use App\Helpers\Entities\Commands\EntityCommandsHelper;
use App\Models\CustomDatamodel;


class InactivityAlarmConditionResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $customDatamodel = CustomDatamodel::where('command', $this->measure)->first();

        $measure_name = EntityCommandsHelper::getCommandNameFromCSV($customDatamodel) ?? RealtimeEntityResourcesHelper::camelCaseToSpaced($this->measure);

        return [
            'id' => (int) $this->id,
            'alarmId' => (int) $this->alarm_id,
            'entity' => EntityResource::make($this->entity),
            'measure' => (array) $this->measure ? [
                'id' => (string) $this->measure,
                'name' => (string) $measure_name,
            ] : null,
            'timeoutS' => (int) $this->timeout_s,
        ];
    }
}
