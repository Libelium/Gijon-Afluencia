<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class DefaultPermissionsResource extends JsonResource
{
    /**
     * Disable wrapping of the resource.
     *
     * @var bool
     */
    public static $wrap = null;

    /**
     * Customize the outgoing response for the resource.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Illuminate\Http\Response  $response
     * @return void
     */
    public function withResponse($request, $response)
    {
        if ($request->header('X-Permissions') === 'true') {
            try {
                $permissions = $this->permissions();
            } catch (\Exception $e) {
                $permissions = [];
            }

            // Add the permissions to the response headers
            $response->headers->set('X-Permissions', json_encode($permissions));
        }
    }
}
