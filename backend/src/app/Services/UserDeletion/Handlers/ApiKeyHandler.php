<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\ApiKey;
use App\Models\User;

class ApiKeyHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers the API key from one user to another.
     * If the destination already has an API key, the source's is deleted to avoid duplicates.
     *
     * @param User $from User whose API key will be transferred.
     * @param User $to User who will receive the API key.
     * @param string|null $modelClass Unused — model is hardcoded to ApiKey.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        $fromKey = ApiKey::where('user_id', $from->id)->first();

        if (!$fromKey) {
            return;
        }

        $toKey = ApiKey::where('user_id', $to->id)->first();

        if ($toKey) {
            $fromKey->delete();
        } else {
            $fromKey->user_id = $to->id;
            $fromKey->save();
        }
    }

    /**
     * Deletes the API key belonging to the given user.
     *
     * @param User $user User whose API key will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to ApiKey.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        ApiKey::where('user_id', $user->id)->delete();
    }
}
