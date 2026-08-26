<?php

namespace App\Http\V1\Resources\Realtime;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;

class EntityRelationshipResource extends JsonResource
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
            'urn' => $this->urn,
            'tenant' => $this->tenant,
            'scope' => $this->scope,
            'id' => $this->name,
            'name' => RealtimeEntityResourcesHelper::camelCaseToSpaced($this->name),
            'value' => $this->value,
            'type' => 'Relationship',
            'value_type' => $this->value_type,
            'timestamp' => $this->timestamp,
            'last_sent' => $this->last_sent,
            'referenced_data' => $this->referenced_data,
            'pruned_by_cicle' => $this->pruned_by_cicle
        ];
    }
}
