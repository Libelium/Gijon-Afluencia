<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\DeletableWithUserInterface;
use App\Models\User;
use Illuminate\Support\Facades\DB;

class SpatiePermissionsHandler implements DeletableWithUserInterface
{
    /**
     * Deletes all Spatie roles and permissions assigned to the given user.
     *
     * @param User $user User whose roles and permissions will be deleted.
     * @param string|null $modelClass Unused — tables are hardcoded to model_has_roles and model_has_permissions.
     * @return void
     */
    public static function deleteForUser(User $user, ?string $modelClass = null): void
    {
        DB::table('model_has_roles')
            ->where('model_id', $user->id)
            ->where('model_type', User::class)
            ->delete();

        DB::table('model_has_permissions')
            ->where('model_id', $user->id)
            ->where('model_type', User::class)
            ->delete();
    }
}
