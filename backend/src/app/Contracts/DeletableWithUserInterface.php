<?php

namespace App\Contracts;

use App\Models\User;

/**
 * Defines the contract for handlers that delete resources
 * associated with a user when that user is removed from the system.
 */
interface DeletableWithUserInterface
{
    /**
     * Deletes all resources associated with $user.
     *
     * @param class-string|null $modelClass
     */
    public static function deleteForUser(User $user, ?string $modelClass = null): void;
}
