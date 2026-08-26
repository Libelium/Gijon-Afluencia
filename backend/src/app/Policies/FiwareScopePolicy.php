<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use Spatie\Permission\Models\Role;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Models\FiwareScope;

class FiwareScopePolicy
{
    use HandlesAuthorization;

    protected $tenant_policy;

    public function __construct(FiwareTenantPolicy $tenant_policy)
    {
        $this->tenant_policy = $tenant_policy;
    }


    /**
     * Checks if the user can read the scope.
     *
     * @param \App\Models\User $user
     * @param \App\Models\FiwareScope $scope
     * @return Response
     */
    public function read(User $user, FiwareScope $scope)
    {
        $scope = $scope->loadMissing('tenant');
        $tenant = $scope->tenant;

        $tenant_permission = $this->tenant_policy->read($user, $tenant);

        if ($tenant_permission->allowed()) {
            return Response::allow();
        }

        $can_read_scope = $user->hasResourcePermissionTo(AppResourcePermission::READ, $scope);

        if (!$can_read_scope) {
            return Response::deny('You are not allowed to read the scope');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the scope.
     *
     * @param \App\Models\User $user
     * @param \App\Models\FiwareScope $scope
     * @return Response
     */
    public function update(User $user, FiwareScope $scope)
    {
        $scope = $scope->loadMissing('tenant');
        $tenant = $scope->tenant;

        $tenant_permission = $this->tenant_policy->update($user, $tenant);

        if ($tenant_permission->allowed()) {
            return Response::allow();
        }

        $can_update_scope = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $scope);

        if (!$can_update_scope) {
            return Response::deny('You are not allowed to update the scope');
        }

        return Response::allow();
    }
}
