<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;
use App\Models\Panel;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

/**
 * Authorization for panels.
 *
 * A panel has no permissions of its own: it always belongs to a dashboard, and the resource
 * permissions live on that dashboard (see DashboardPolicy and model_has_resource_permissions,
 * which never holds `panels` rows). So every decision here is delegated to the owning dashboard
 * with exactly the same rules DashboardPolicy applies.
 *
 * A panel whose dashboard is missing is denied: an orphan panel has no owner to authorize
 * against, so the safe answer is "no".
 */
class PanelPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the panel, i.e. can read the dashboard it belongs to.
     */
    public function read(User $user, Panel $panel): Response
    {
        $dashboard = $this->dashboardOf($panel);

        if (!$dashboard) {
            return Response::deny('The panel does not belong to any dashboard');
        }

        if (!$user->can(AppPermission::DASHBOARDS_READ->value)) {
            return Response::deny('You are not allowed to access the dashboards module');
        }

        if (!$user->hasResourcePermissionTo(AppResourcePermission::READ, $dashboard)) {
            return Response::deny('You are not allowed to read the panel');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the panel, i.e. can update the dashboard it belongs to.
     */
    public function update(User $user, Panel $panel): Response
    {
        $dashboard = $this->dashboardOf($panel);

        if (!$dashboard) {
            return Response::deny('The panel does not belong to any dashboard');
        }

        return $this->updateDashboard($user, $dashboard);
    }

    /**
     * Checks if the user can delete the panel. Deleting a panel is editing its dashboard,
     * so it requires the same permission as updating it (same rule as DashboardPolicy).
     */
    public function delete(User $user, Panel $panel): Response
    {
        return $this->update($user, $panel);
    }

    /**
     * Checks if the user can add a panel to the given dashboard. The dashboard is passed
     * explicitly because there is no panel yet:
     *
     *     $this->authorize('create', [Panel::class, $dashboard]);
     */
    public function create(User $user, ?Dashboard $dashboard = null): Response
    {
        if (!$dashboard) {
            return Response::deny('A dashboard is required to create a panel');
        }

        return $this->updateDashboard($user, $dashboard);
    }

    /**
     * The shared "may this user edit this dashboard?" rule.
     */
    private function updateDashboard(User $user, Dashboard $dashboard): Response
    {
        if (!$user->can(AppPermission::DASHBOARDS_UPDATE->value)) {
            return Response::deny('You are not allowed to update the dashboards module');
        }

        if (!$user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $dashboard)) {
            return Response::deny('You are not allowed to update the dashboard');
        }

        return Response::allow();
    }

    /**
     * The dashboard a panel belongs to, or null when the relation is broken.
     */
    private function dashboardOf(Panel $panel): ?Dashboard
    {
        $panel->loadMissing('dashboard');

        return $panel->dashboard;
    }
}
