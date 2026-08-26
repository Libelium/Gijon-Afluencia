<?php

namespace App\Policies;

use App\Repositories\PermissionRepository;

use App\Models\Reports\Report;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;

class ReportPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the report.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Reports\Report $report
     * @return void|bool
     */
    public function read(User $user, Report $report): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_reports = $user->can(AppPermission::REPORTS_READ->value);

        if (!$can_reports) {
            return Response::deny('You are not allowed to read reports');
        }

        $can_read_report = $user->hasResourcePermissionTo(AppResourcePermission::READ, $report);

        if (!$can_read_report) {
            return Response::deny('You are not allowed to read this report');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create the report.
     * @param User $user
     * @return bool|mixed
     */
    public function create(User $user): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        ResourceLimitsHelper::canCreateOrFail($user, Report::class);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_reports = $user->can(AppPermission::REPORTS_UPDATE->value);

        if (!$can_reports) {
            return Response::deny('You are not allowed to update reports');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the report.
     * @param User $user
     * @param Report $report
     * @return bool|mixed
     */
    public function update(User $user, Report $report)
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_reports = $user->can(AppPermission::REPORTS_UPDATE->value);

        if (!$can_reports) {
            return Response::deny('You are not allowed to update reports');
        }

        $can_update_report = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $report);

        if (!$can_update_report) {
            return Response::deny('You are not allowed to update this report');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the report.
     * @param User $user
     * @param Report $report
     * @return bool|mixed
     */
    public function delete(User $user, Report $report)
    {
        return $this->update($user, $report);
    }
}
