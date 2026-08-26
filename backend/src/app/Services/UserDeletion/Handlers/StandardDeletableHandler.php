<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\DeletableWithUserInterface;
use App\Models\User;

/**
 * Generic handler for models that must be deleted when a user is removed.
 * Use this for any model where deleteForUser = DELETE WHERE user_id.
 *
 * For email-keyed tables (e.g. password_resets) create a dedicated handler.
 */
class StandardDeletableHandler implements DeletableWithUserInterface
{
    /**
     * Deletes all records of the given model class belonging to the user.
     *
     * @param User $user User whose records will be deleted.
     * @param class-string|null $modelClass Eloquent model class to delete from.
     * @return void
     */
    public static function deleteForUser(User $user, ?string $modelClass = null): void
    {
        $modelClass::where('user_id', $user->id)->delete();
    }
}
