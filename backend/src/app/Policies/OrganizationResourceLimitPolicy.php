<?php

namespace App\Policies;

use App\Models\User;
use App\Models\UserResourceLimit;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class OrganizationResourceLimitPolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can view any resource limits of a given user.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\User  $resourceOwner
     * @return \Illuminate\Auth\Access\Response
     */
    public function viewAny(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_RESOURCE_LIMITS_UPDATE->value)
            ? Response::allow()
            : Response::deny('No tiene permiso para ver límites de recursos');
    }

    /**
     * Determine whether the user can create (or upsert) a resource limit for a user.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\User  $resourceOwner
     * @return \Illuminate\Auth\Access\Response
     */
    public function create(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_RESOURCE_LIMITS_UPDATE->value)
            ? Response::allow()
            : Response::deny('No tiene permiso para crear límites de recursos');
    }

    /**
     * Determine whether the user can update the specified resource limit.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\UserResourceLimit  $limit
     * @return \Illuminate\Auth\Access\Response
     */
    public function update(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_RESOURCE_LIMITS_UPDATE->value)
            ? Response::allow()
            : Response::deny('No tiene permiso para actualizar límites de recursos');
    }

    /**
     * Determine whether the user can delete the specified resource limit.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\UserResourceLimit  $limit
     * @return \Illuminate\Auth\Access\Response
     */
    public function delete(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_RESOURCE_LIMITS_UPDATE->value)
            ? Response::allow()
            : Response::deny('No tiene permiso para eliminar límites de recursos');
    }
}
