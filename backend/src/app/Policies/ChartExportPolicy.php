<?php

namespace App\Policies;

use App\Models\ChartExports\ChartExport;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;

class ChartExportPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the chart export.
     */
    public function read(User $user, ChartExport $chartExport): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_chart_exports = $user->can(AppPermission::CHART_EXPORTS_READ->value);

        if (!$can_chart_exports) {
            return Response::deny('You are not allowed to read chart exports');
        }

        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $chartExport);

        if (!$can_read) {
            return Response::deny('You are not allowed to read this chart export');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create a chart export.
     */
    public function create(User $user): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        ResourceLimitsHelper::canCreateOrFail($user, ChartExport::class);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_chart_exports = $user->can(AppPermission::CHART_EXPORTS_UPDATE->value);

        if (!$can_chart_exports) {
            return Response::deny('You are not allowed to create chart exports');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the chart export.
     */
    public function update(User $user, ChartExport $chartExport)
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_chart_exports = $user->can(AppPermission::CHART_EXPORTS_UPDATE->value);

        if (!$can_chart_exports) {
            return Response::deny('You are not allowed to update chart exports');
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $chartExport);

        if (!$can_update) {
            return Response::deny('You are not allowed to update this chart export');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the chart export.
     */
    public function delete(User $user, ChartExport $chartExport)
    {
        return $this->update($user, $chartExport);
    }
}
