<?php

namespace App\Http\V1\Resources;

use App\Authorization\AppPermission;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class FiwareServiceResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * SECURITY: `apikey` is the IoT Agent credential that lets a client post measurements as any
     * device of the service, so it is NOT part of the general service listing. It is only
     * included for users who hold `data_sources.read` — the same permission that gates the device
     * simulator (FiwareTenantScopeController::getFiwareManagerUrl / proxyFiwareManagerCommand),
     * which is the only consumer that needs the key. Everyone else gets the service metadata
     * without the credential.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        return [
            'tenant' => $this["service"],
            'scope' => $this["subservice"],
            'apikey' => $this->when($this->canReadApikey(), fn() => $this["apikey"]),
            'entity_type' => $this["entity_type"],
            'device_type' => $this["internal_attributes"][0]['device_type_code'] ?? null,
            'attributes' => $this["attributes"] ?? [],
        ];
    }

    /**
     * Whether the current user may see the raw IoT Agent apikey.
     */
    private function canReadApikey(): bool
    {
        $user = Auth::user();

        return $user !== null && $user->can(AppPermission::DATA_SOURCES_READ->value);
    }
}
