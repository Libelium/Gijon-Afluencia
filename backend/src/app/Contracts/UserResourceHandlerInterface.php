<?php

namespace App\Contracts;

use App\Models\User;

/**
 * Defines the contract for classes that handle the transfer or cleanup
 * of resources owned by a user, as part of the user deletion process.
 */
interface UserResourceHandlerInterface
{
    /**
     * Transfers all resources owned by $from to $to.
     *
     * @param class-string $modelClass
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void;

    /**
     * Deletes or detaches all resources owned by $user.
     *
     * @param class-string $modelClass
     */
    public static function clean(User $user, ?string $modelClass = null): void;
}
