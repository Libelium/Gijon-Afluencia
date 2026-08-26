<?php

namespace App\Http\V1\Resources;

use App\Repositories\PreferenceRepository;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;


class OrganizationResource extends JsonResource
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
            'id' => $this->id,
            'name' => $this->name,
            'admin' => [
                'id' => $this->adminUser->id,
                'name' => $this->adminUser->name,
                'email' => $this->adminUser->email,
            ]
        ];
    }

    /**
     * Transform the resource into an array.
     *
     * @return array
     */
    public function toArrayWithBpId()
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'admin' => [
                'id' => $this->adminUser->id,
                'name' => $this->adminUser->name,
                'email' => $this->adminUser->email,
            ],
            'bp_id' => $this->bp_id
        ];
    }
}
