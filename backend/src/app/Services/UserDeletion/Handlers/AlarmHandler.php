<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\Alarm;
use App\Models\Actions\AlarmHasAction;
use App\Models\User;

class AlarmHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers all alarms from one user to another.
     *
     * @param User $from User whose alarms will be transferred.
     * @param User $to User who will receive the alarms.
     * @param string|null $modelClass Unused — model is hardcoded to Alarm.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        Alarm::where('user_id', $from->id)->update(['user_id' => $to->id]);
    }

    /**
     * Deletes all alarms belonging to the given user.
     * Pivot rows in alarm_has_actions are removed first to avoid FK violations.
     *
     * @param User $user User whose alarms will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to Alarm.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        $alarmIds = Alarm::where('user_id', $user->id)->pluck('id');
        AlarmHasAction::whereIn('alarm_id', $alarmIds)->delete();

        Alarm::where('user_id', $user->id)->delete();
    }
}
