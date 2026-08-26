<?php

namespace App\Policies;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Helpers\ResourceLimitsHelper;
use App\Models\Dashboard;
use App\Models\ResourceLimit;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class DashboardPolicy
{

    use HandlesAuthorization;

    /**
     * Checks if the user can read the dashboard
     * @param \App\Models\User $user
     * @param \App\Models\Dashboard $dashboard
     * @return \Response
     */
    public function read(User $user, Dashboard $dashboard): Response
    {
        $allowed = $user->can(AppPermission::DASHBOARDS_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to access the dashboards module');
        }

        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $dashboard);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the dashboard');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the dashboard
     * @param \App\Models\User $user
     * @param \App\Models\Dashboard $dashboard
     * @return \Response
     */
    public function update(User $user, Dashboard $dashboard): Response
    {
        $allowed = $user->can(AppPermission::DASHBOARDS_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to update the dashboards module');
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $dashboard);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the dashboard');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the dashboard. A user can delete a dashboard 
     * if they have the permission to update it.
     * @param \App\Models\User $user
     * @param \App\Models\Dashboard $dashboard
     * @return \Response
     */
    public function delete(User $user, Dashboard $dashboard): Response
    {
        return $this->update($user, $dashboard);
    }

    /**
     * Checks if the user can create a new dashboard.
     * @param \App\Models\User $user
     * @param \App\Models\Dashboard $dashboard
     * @return \Response
     */
    public function create(User $user): Response
    {
        $allowed = $user->hasAllPermissions([
            AppPermission::DASHBOARDS_UPDATE->value,
            AppPermission::ANALYTICS_READ->value,
        ]);

        ResourceLimitsHelper::canCreateOrFail($user, Dashboard::class);

        if (!$allowed) {
            return Response::deny('You are not allowed to create dashboards');
        }

        return Response::allow();
    }

    /**
     * Determines if the user can list dashboards.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function list(User $user): Response
    {
        $allowed = $user->can(AppPermission::DASHBOARDS_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to access the dashboards module');
        }

        return Response::allow();
    }
}