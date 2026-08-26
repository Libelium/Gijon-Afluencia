<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\Actions\Action;
use App\Models\Actions\ActionEmail;
use App\Models\User;

class ActionHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers all actions from one user to another and updates email references.
     *
     * @param User $from User whose actions will be transferred.
     * @param User $to User who will receive the actions.
     * @param string|null $modelClass Unused — model is hardcoded to Action.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        Action::where('user_id', $from->id)
            ->update(['user_id' => $to->id]);

        static::replaceEmailInActionEmails($from->email, $to->email);
    }

    /**
     * Deletes all actions belonging to the given user.
     *
     * @param User $user User whose actions will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to Action.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        Action::where('user_id', $user->id)->delete();
    }

    /**
     * Replaces occurrences of an old email with a new one in ActionEmail destinations.
     *
     * @param string $oldEmail Email to be replaced.
     * @param string $newEmail Replacement email.
     * @return void
     */
    private static function replaceEmailInActionEmails(string $oldEmail, string $newEmail): void
    {
        ActionEmail::where('destination', 'LIKE', '%' . $oldEmail . '%')
            ->get()
            ->each(function (ActionEmail $actionEmail) use ($oldEmail, $newEmail) {
                $updated = array_map(
                    fn (string $email) => $email === $oldEmail ? $newEmail : $email,
                    $actionEmail->destination
                );

                $actionEmail->destination = $updated;
                $actionEmail->save();
            });
    }
}
