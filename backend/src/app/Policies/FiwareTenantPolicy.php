<?php

namespace App\Policies;

use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Models\User;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Models\FiwareTenant;

class FiwareTenantPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the tenant.
     *
     * @param \App\Models\User $user
     * @param \App\Models\FiwareTenant $tenant
     * @return Response
     */
    public function read(User $user, FiwareTenant $tenant): Response
    {
        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $tenant);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the tenant');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the tenant.
     *
     * @param \App\Models\User $user
     * @param \App\Models\FiwareTenant $tenant
     * @return Response
     */
    public function update(User $user, FiwareTenant $tenant): Response
    {
        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $tenant);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the tenant');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can read tenants from the administration view.
     *
     * @param \App\Models\User $user
     * @return Response
     */
    public function administrationRead(User $user): Response
    {
        return $user->can(AppPermission::ADMINISTRATION_FIWARE_TENANTS_READ->value)
            ? Response::allow()
            : Response::deny('You are not allowed to read FIWARE tenants.');
    }

    /**
     * Checks if the user can create tenants from the administration view.
     *
     * @param \App\Models\User $user
     * @return Response
     */
    public function administrationUpdate(User $user): Response
    {
        return $user->can(AppPermission::ADMINISTRATION_FIWARE_TENANTS_UPDATE->value)
            ? Response::allow()
            : Response::deny('You are not allowed to create FIWARE tenants.');
    }
}
