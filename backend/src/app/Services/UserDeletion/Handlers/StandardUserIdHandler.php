<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\User;

/**
 * Generic handler for models that only need a user_id column update.
 * Use this for any model where transfer = UPDATE user_id and clean = DELETE.
 *
 * For models with special logic (S3 deletion, dedup, etc.) create a dedicated handler.
 */
class StandardUserIdHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers all records of the given model class from one user to another.
     *
     * @param User $from User whose records will be transferred.
     * @param User $to User who will receive the records.
     * @param class-string|null $modelClass Eloquent model class to update.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        $modelClass::where('user_id', $from->id)
            ->update(['user_id' => $to->id]);
    }

    /**
     * Deletes all records of the given model class belonging to the user.
     *
     * @param User $user User whose records will be deleted.
     * @param class-string|null $modelClass Eloquent model class to delete from.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        $modelClass::where('user_id', $user->id)
            ->delete();
    }
}
