<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class HomeLayoutResource extends JsonResource
{
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'userId' => $this->user_id,
            'name' => $this->name,
            'layout' => $this->layout,
            'responsiveLayout' => $this->responsive_layout,
        ];
    }
}
