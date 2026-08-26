<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class HomeWidgetResource extends JsonResource
{
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'userId' => $this->user_id,
            'homeLayoutId' => $this->home_layout_id,
            'type' => $this->type,
            'config' => $this->config,
        ];
    }
}
