<?php

namespace App\Policies;

use App\Repositories\PermissionRepository;

use App\Models\Reports\ReportDocConfig;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;

class ReportDocConfigPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the ReportDocConfig.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Reports\ReportDocConfig $reportDocConfigDocConfig
     * @return void|bool
     */
    public function read(User $user, ReportDocConfig $reportDocConfigDocConfig): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_Reports = $user->can(AppPermission::REPORTS_READ->value);

        if (!$can_Reports) {
            return Response::deny('You are not allowed to read Reports');
        }

        $can_read_ReportDocConfig = $user->hasResourcePermissionTo(
            AppResourcePermission::READ,
            $reportDocConfigDocConfig
        );

        if (!$can_read_ReportDocConfig) {
            return Response::deny('You are not allowed to read this ReportDocConfig');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create the ReportDocConfig.
     * @param User $user
     * @return bool|mixed
     */
    public function create(User $user): Response
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_Reports = $user->can(AppPermission::REPORTS_UPDATE->value);

        if (!$can_Reports) {
            return Response::deny('You are not allowed to update Reports');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the ReportDocConfig.
     * @param User $user
     * @param ReportDocConfig $reportDocConfigDocConfig
     * @return bool|mixed
     */
    public function update(User $user, ReportDocConfig $reportDocConfigDocConfig)
    {
        $can_analytics = $user->can(AppPermission::ANALYTICS_READ->value);

        if (!$can_analytics) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        $can_Reports = $user->can(AppPermission::REPORTS_UPDATE->value);

        if (!$can_Reports) {
            return Response::deny('You are not allowed to update Reports');
        }

        $can_update_ReportDocConfig = $user->hasResourcePermissionTo(
            AppResourcePermission::UPDATE,
            $reportDocConfigDocConfig
        );

        if (!$can_update_ReportDocConfig) {
            return Response::deny('You are not allowed to update this ReportDocConfig');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the ReportDocConfig.
     * @param User $user
     * @param ReportDocConfig $reportDocConfigDocConfig
     * @return bool|mixed
     */
    public function delete(User $user, ReportDocConfig $reportDocConfigDocConfig)
    {
        return $this->update($user, $reportDocConfigDocConfig);
    }
}
