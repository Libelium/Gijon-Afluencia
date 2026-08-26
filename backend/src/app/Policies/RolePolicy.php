<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use Spatie\Permission\Models\Role;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;

class RolePolicy
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
    public function read(User $user, Role $role)
    {
        $can_read = $user->can(AppPermission::ROLES_READ->value);

        if (!$can_read) {
            return Response::deny('You are not allowed to read roles');
        }

        $allowed = $can_read && $user->organization_id === $role->organization_id;

        if (!$allowed) {
            return Response::deny('You are not allowed to read the role ' . $role->id . ', as it does not belong to your organization');
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
        $allowed = $user->can(AppPermission::ROLES_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to list roles');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can update the role.
     * 
     * @param \App\Models\User  $user
     * @param \Spatie\Permission\Models\Role  $role
     */
    public function update(User $user, Role $role)
    {
        $can_update = $user->can(AppPermission::ROLES_UPDATE->value);

        if (!$can_update) {
            return Response::deny('You are not allowed to update roles');
        }

        $allowed = $can_update && $user->organization_id === $role->organization_id;

        if (!$allowed) {
            return Response::deny('You are not allowed to update the role ' . $role->id . ', as it does not belong to your organization');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can create a role
     * 
     * @param \App\Models\User  $user
     * @param \Spatie\Permission\Models\Role  $role
     */
    public function create(User $user, Role $role)
    {
        $allowed = $user->can(AppPermission::ROLES_UPDATE->value);

        ResourceLimitsHelper::canCreateOrFail($user, Role::class);

        if (!$allowed) {
            return Response::deny('You are not allowed to create roles');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can delete the role.
     * 
     * @param \App\Models\User  $user
     * @param \Spatie\Permission\Models\Role  $role
     */
    public function delete(User $user, Role $role)
    {
        return $this->update($user, $role);
    }

    /**
     * Determine whether the user can assign a role to a user.
     * 
     * @param \App\Models\User  $user
     * @param \Spatie\Permission\Models\Role  $role
     * @param \App\Models\User  $assignee
     */
    public function assign(User $user, Role $role, User $assignee)
    {
        $can_assign = $user->can(AppPermission::ROLES_UPDATE->value);

        if (!$can_assign) {
            return Response::deny('You are not allowed to assign roles');
        }

        $is_same_organization = $user->organization_id === $role->organization_id;

        if (!$is_same_organization) {
            return Response::deny('You are not allowed to assign the role ' . $role->id . ' as it does not belong to your organization');
        }

        $assignee_is_same_organization = $user->organization_id === $assignee->organization_id;

        if (!$assignee_is_same_organization) {
            return Response::deny('You are not allowed to assign the role ' . $role->name . ' to the user ' . $assignee->name . ' as it does not belong to the same organization');
        }

        if ($role->organization_id === null) {
            return Response::deny('You are not allowed to assign a global role ' . $role->name);
        }

        return Response::allow();
    }
}
