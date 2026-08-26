<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class DefaultPaginationResource extends JsonResource
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
        return [
            'rows' => $this['rows'],
            'count' => $this['count'],
        ];
    }

    /**
     * Customize the outgoing response for the resource.
     *
     * This method is optimized to return only unique permissions.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \Illuminate\Http\Response  $response
     * @return void
     */
    public function withResponse($request, $response)
    {
        // Check if the client requested the permissions header.
        if ($request->header('X-Permissions') === 'true') {
            // Use Laravel's collection methods for a clean and efficient solution.
            $uniquePermissions = collect($this['items'])
                /**
                 * 1. `flatMap` iterates over each item and its permissions.
                 * It returns a single, flat collection of all permissions,
                 * replacing the need for a `for` loop and `array_merge`.
                 */
                ->flatMap(function ($item) {
                    // The permissions() method is expected to return an array or Collection
                    // of permission objects or associative arrays.
                    return $item->permissions();
                })
                /**
                 * 2. `unique` filters the collection to remove duplicates.
                 * We provide a callback to define what makes an item unique.
                 * In this case, it's the combination of 'resource' and 'action'.
                 */
                ->unique(function ($permission) {
                    // The items in the collection could be objects or associative arrays.
                    // This handles both cases to ensure robustness.
                    $resource = is_array($permission) ? $permission['resource'] : $permission->resource;
                    $action = is_array($permission) ? $permission['action'] : $permission->action;
                    
                    // Create a unique identifier string for each resource-action pair.
                    return $resource . '|' . $action;
                })
                /**
                 * 3. `values` resets the array keys to ensure it's a zero-indexed
                 * array (e.g., 0, 1, 2...), which is necessary for correct
                 * JSON array encoding.
                 */
                ->values()
                /**
                 * 4. `all` converts the final Laravel Collection back into a plain PHP array.
                 */
                ->all();

            // Add the unique permissions to the response headers as a JSON string.
            $response->headers->set('X-Permissions', json_encode($uniquePermissions));
        }
    }
}
