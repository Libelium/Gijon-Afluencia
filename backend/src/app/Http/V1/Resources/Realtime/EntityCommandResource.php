<?php

namespace App\Http\V1\Resources\Realtime;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use App\Helpers\Entities\Commands\EntityCommandsHelper;
use App\Models\CustomDatamodel;

class EntityCommandResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $customDatamodel = CustomDatamodel::where('command', $this->name)->first();

        $name = EntityCommandsHelper::getCommandNameFromCSV($customDatamodel) ?? RealtimeEntityResourcesHelper::camelCaseToSpaced($this->name);

        $isInternal = EntityCommandsHelper::getCommandPropertyFromCSV("internal", $customDatamodel);

        return [
            'urn' => $this->urn,
            'tenant' => $this->tenant,
            'scope' => $this->scope,
            'entity_id' => $this->entity_id,
            'id' => $this->name,
            'name' => $name,
            'status' => RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($this->status),
            'info' => RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($this->info),
            'status_timestamp' => $this->status_timestamp,
            'info_timestamp' => $this->info_timestamp,
            'timestamp' => max($this->status_timestamp, $this->info_timestamp),
            'type' => 'Command',
            'value_type' => $this->value_type,
            'available' => $this->available,
            'pending' => $this->pending,
            'pending_value' => RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($this->pending_value),
            'current_value' => RealtimeEntityResourcesHelper::castValueTo($this->current_value, $this->value_type),
            'description' => EntityCommandsHelper::getCommandDescriptionFromCSV($customDatamodel) ?? "No info available",
            'data_type' => EntityCommandsHelper::getCommandDataTypeFromCSV($customDatamodel),
            'units' => EntityCommandsHelper::getCommandPropertyFromCSV("units", $customDatamodel),
            'tab' => EntityCommandsHelper::getCommandPropertyFromCSV("tab", $customDatamodel),
            'datamodel' => EntityCommandsHelper::getCommandPropertyFromCSV("datamodel", $customDatamodel),
            "max_value" => EntityCommandsHelper::getCommandPropertyFromCSV("max", $customDatamodel),
            "min_value" => EntityCommandsHelper::getCommandPropertyFromCSV("min", $customDatamodel),
            "internal" => $isInternal === "Yes" ? true : false,
            "operations" => EntityCommandsHelper::getCommandOperationsFromCSV($customDatamodel),
        ];
    }
}
