<?php

namespace App\Http\V1\Resources;

use App\Http\V1\Resources\OrganizationResource;
use App\Repositories\PreferenceRepository;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;


class UserResource extends JsonResource
{
    private function getInheritedPermissions()
    {
        $organization = Auth::user()->organization;

        $admin = $organization->adminUser;

        $permissions = $admin->getAllPermissions();

        $filtered_permissions = $permissions->filter(function ($permission) {
            return preg_match('/dashboards\..*\.read/', $permission->name) ||
                   preg_match('/home_layouts\..*/', $permission->name) || 
                   preg_match('/openweather\..*/', $permission->name);
        });

        $permission_array = [];

        foreach ($filtered_permissions as $permission) {
            $permission_array[] = [
                'id' => $permission->id,
                'name' => $permission->name,
            ];
        }

        return $permission_array;
    }

    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $preferences = PreferenceRepository::getUserPreferences();

        $roles = $this->roles->map(function ($role) {
            return [
                'id' => $role->id,
                'name' => $role->name,
            ];
        });

        $permissions = $this->getAllPermissions()->map(function ($permission) {
            return [
                'id' => $permission->id,
                'name' => $permission->name,
            ];
        })->toArray();

        $inherited_permissions = $this->getInheritedPermissions();

        $final_permissions = array_merge($inherited_permissions, $permissions);

        $user_resource = [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->email,
            'enabled' => $this->enabled,
            'preferences' => $preferences,
            'organization' => new OrganizationResource($this->organization),
            'roles' => $roles,
            'permissions' => $final_permissions,
            'created_at' => $this->created_at->format('Y-m-d H:i:s'),
            'blocked_by_admin' => $this->blocked_by_admin,
        ];

        return $user_resource;
    }
}
