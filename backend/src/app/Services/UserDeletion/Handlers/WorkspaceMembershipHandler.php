<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\User;
use Illuminate\Support\Facades\DB;

class WorkspaceMembershipHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers workspace memberships from one user to another.
     * Overlapping memberships are removed first to avoid unique constraint violations.
     *
     * @param User $from User whose memberships will be transferred.
     * @param User $to User who will receive the memberships.
     * @param string|null $modelClass Unused — table is hardcoded to workspace_has_users.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        DB::table('workspace_has_users')
            ->where('user_id', $from->id)
            ->whereIn('workspace_id', function ($query) use ($to) {
                $query->select('workspace_id')
                    ->from('workspace_has_users')
                    ->where('user_id', $to->id);
            })
            ->delete();

        DB::table('workspace_has_users')
            ->where('user_id', $from->id)
            ->update(['user_id' => $to->id]);
    }

    /**
     * Removes all workspace memberships belonging to the given user.
     *
     * @param User $user User whose memberships will be deleted.
     * @param string|null $modelClass Unused — table is hardcoded to workspace_has_users.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        DB::table('workspace_has_users')
            ->where('user_id', $user->id)
            ->delete();
    }
}
