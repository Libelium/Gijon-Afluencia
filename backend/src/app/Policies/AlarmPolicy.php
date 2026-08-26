<?php

namespace App\Policies;

use App\Authorization\AppResourcePermission;
use App\Models\Alarm;
use App\Models\User;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Models\ResourceLimit;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;

class AlarmPolicy
{
    use HandlesAuthorization;

    public function max_alarms_exceeded(User $user)
    {
        // check if running on premise
        $onPremise = config('app.on_premise.enabled');

        if ($onPremise) {
            return false;
        }

        $maxAlarms = config('app.limits.users.alarms.max');

        // check number of alarms of the user
        $numAlarms = Alarm::where('user_id', $user->id)->count();

        if ($numAlarms < $maxAlarms) {
            return false;
        }

        return true;
    }

    /**
     * A user can create an alarm if he has the permission to update alarms
     * and the maximum number of alarms has not been reached
     * 
     * @param \App\Models\User $user
     * @return Response
     */
    public function create(User $user): Response
    {
        $can_create_alarms = $user->can(AppPermission::ALARMS_UPDATE->value);

        ResourceLimitsHelper::canCreateOrFail($user, Alarm::class);

        if (!$can_create_alarms) {
            return Response::deny('You are not allowed to create alarms');
        }

        if ($this->max_alarms_exceeded($user)) {
            return Response::deny('You have reached the maximum number of alarms');
        }

        return Response::allow();
    }

    /**
     * A user can update an alarm if he has the permission to update alarms,
     * and the update permission over the alarm
     * 
     * @param \App\Models\User $user
     * @param \App\Models\Alarm $alarm
     */

    public function update(User $user, Alarm $alarm): Response
    {
        $can_update_alarms = $user->can(AppPermission::ALARMS_UPDATE->value);

        if (!$can_update_alarms) {
            return Response::deny('You are not allowed to update alarms');
        }

        $can_update_alarm = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $alarm);

        if (!$can_update_alarm) {
            return Response::deny('You are not allowed to update this alarm');
        }

        return Response::allow();
    }

    /**
     * A user can delete an alarm if he has the permission to update alarms,
     * and the delete permission over the alarm
     * 
     * @param \App\Models\User $user
     * @param \App\Models\Alarm $alarm
     */
    public function delete(User $user, Alarm $alarm): Response
    {
        return $this->update($user, $alarm);
    }

    /**
     * A user can read an alarm if he has the permission to read alarms,
     * 
     * @param \App\Models\User $user
     * @param \App\Models\Alarm $alarm
     */
    public function read(User $user, Alarm $alarm): Response
    {
        $can_read_alarms = $user->can(AppPermission::ALARMS_READ->value);

        if (!$can_read_alarms) {
            return Response::deny('You are not allowed to read alarms');
        }

        $can_read_alarm = $user->hasResourcePermissionTo(AppResourcePermission::READ, $alarm);

        if (!$can_read_alarm) {
            return Response::deny('You are not allowed to read this alarm');
        }

        return Response::allow();
    }
}
