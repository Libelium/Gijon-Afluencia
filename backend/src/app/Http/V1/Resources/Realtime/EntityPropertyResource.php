<?php

namespace App\Http\V1\Resources\Realtime;

use Illuminate\Http\Resources\Json\JsonResource;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use App\Helpers\Entities\Commands\EntityCommandsHelper;
use App\Models\CustomDatamodel;

class EntityPropertyResource extends JsonResource
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

        return [
            'urn' => $this->urn,
            'tenant' => $this->tenant,
            'scope' => $this->scope,
            'entity_id' => $this->entity_id,
            'id' => $this->name,
            'name' => $name,
            'value_type' => $this->value_type,
            'value' => RealtimeEntityResourcesHelper::castValueTo($this->value, $this->value_type),
            'type' => 'Property',
            'description' => EntityCommandsHelper::getCommandDescriptionFromCSV($customDatamodel) ?? "No info available",
            'units' => EntityCommandsHelper::getCommandPropertyFromCSV("units", $customDatamodel) ?? $this->units,
            'timestamp' => $this->timestamp,
            'template' => EntityCommandsHelper::getCommandPropertyFromCSV("template", $customDatamodel) ?? $this->units,
            'internal' => EntityCommandsHelper::getCommandPropertyFromCSV("internal", $customDatamodel) ?? false,
        ];
    }
}
