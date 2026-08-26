<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class DefaultArrayResource extends JsonResource
{
    /**
     * Disable wrapping of the resource.
     *
     * @var bool
     */
    public static $wrap = null;

    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        return $this['rows'];
    }

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
            $permissions = [];

            for ($i = 0; $i < count($this['items']); $i++) {
                $permissions[] = $this['items'][$i]->permissions();
            }

            $permissions = array_merge(...collect($permissions)->toArray());

            // Add the permissions to the response headers
            $response->headers->set('X-Permissions', json_encode($permissions));
        }
    }
}
