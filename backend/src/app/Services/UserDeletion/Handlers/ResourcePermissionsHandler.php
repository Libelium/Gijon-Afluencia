<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\DeletableWithUserInterface;
use App\Models\Authorization\ModelHasResourcePermission;
use App\Models\User;

class ResourcePermissionsHandler implements DeletableWithUserInterface
{
    /**
     * Deletes all resource permissions assigned to the given user.
     * Uses getTable() as model_type since ResourcePermissionRepository stores
     * the table name ('users') instead of the FQCN.
     *
     * @param User $user User whose resource permissions will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to ModelHasResourcePermission.
     * @return void
     */
    public static function deleteForUser(User $user, ?string $modelClass = null): void
    {
        ModelHasResourcePermission::where('model_id', $user->id)
            ->where('model_type', $user->getTable())
            ->delete();
    }
}
