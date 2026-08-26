<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use Spatie\Permission\Models\Permission;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;

class PermissionPolicy
{
    use HandlesAuthorization;


    /**
     * Determine whether the user can view the role.
     * Can only view roles that belong to the same organization.
     *
     * @param  \App\Models\User  $user
     * @param  \Spatie\Permission\Models\Role  $role
     * @return mixed
     */
    public function read(User $user, Permission $role)
    {
        $can_read = $user->can(AppPermission::ROLES_READ->value);

        if (!$can_read) {
            return Response::deny('You are not allowed to read permissions');
        }

        return Response::allow();
    }

    /**
     * Determine wether the user can list all roles of the organization.
     * 
     * @param \App\Models\User $user
     */
    public function list(User $user)
    {
        $can_list = $user->can(AppPermission::ROLES_READ->value);

        if (!$can_list) {
            return Response::deny('You are not allowed to list permissions');
        }

        return Response::allow();
    }
}
