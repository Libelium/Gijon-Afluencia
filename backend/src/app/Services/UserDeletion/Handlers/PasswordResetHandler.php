<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\DeletableWithUserInterface;
use App\Models\PasswordReset;
use App\Models\User;

class PasswordResetHandler implements DeletableWithUserInterface
{
    /**
     * Deletes all password reset tokens for the given user.
     * Uses email instead of user_id since password_resets has no FK to users.
     *
     * @param User $user User whose reset tokens will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to PasswordReset.
     * @return void
     */
    public static function deleteForUser(User $user, ?string $modelClass = null): void
    {
        PasswordReset::where('email', $user->email)->delete();
    }
}
