<?php

namespace App\Http\V1\Resources;

use App\Http\V1\Resources\Realtime\EntityPropertyResource;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class EntityHealthcheckResource extends \App\Http\V1\Resources\DefaultPermissionsResource
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
            'device_id' => $this->device_id,
            'serial' => $this->serial,
            'device_type' => $this->device_type,
            'firmware_version' => $this->firmware_version,
            'overall_status' => $this->overall_status,
            'reason' => $this->reason,
            'battery_status' => $this->battery_status,
            'signal_status' => $this->signal_status,
            'send_frequency_status' => $this->send_frequency_status,
            'battery_reason' => $this->battery_reason,
            'signal_reason' => $this->signal_reason,
            'send_frequency_reason' => $this->send_frequency_reason,
            'organization_name' => $this->organization_name,
        ];
    }
}
