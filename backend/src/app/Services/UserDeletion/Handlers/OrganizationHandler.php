<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\Organization;
use App\Models\User;
use Illuminate\Support\Facades\DB;

class OrganizationHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers admin ownership of all organizations from one user to another.
     *
     * @param User $from User who is currently admin of the organizations.
     * @param User $to User who will become the new admin.
     * @param string|null $modelClass Unused — model is hardcoded to Organization.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        Organization::where('admin', $from->id)
            ->update(['admin' => $to->id]);
    }

    /**
     * Deletes all organizations owned by the given user.
     * Members are detached beforehand to prevent the ON DELETE CASCADE
     * on users.organization_id from deleting other user rows.
     *
     * @param User $user User whose organizations will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to Organization.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        Organization::where('admin', $user->id)->each(function (Organization $org) {
            DB::table('users')->where('organization_id', $org->id)
                ->update(['organization_id' => null]);
            $org->delete();
        });
    }
}
