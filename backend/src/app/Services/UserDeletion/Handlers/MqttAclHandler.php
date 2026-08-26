<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\MqttAcl;
use App\Models\MqttUser;
use App\Models\User;

class MqttAclHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers MQTT ACLs from one user to another.
     * If the destination MQTT user does not exist, the source user is renamed.
     * If it does exist, non-duplicate ACLs are merged and the source user is deactivated.
     *
     * @param User $from User whose MQTT ACLs will be transferred.
     * @param User $to User who will receive the MQTT ACLs.
     * @param string|null $modelClass Unused — model is hardcoded to MqttAcl.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        $fromMqttUser = MqttUser::findByUsername($from->email)->first();

        if (!$fromMqttUser) {
            return;
        }

        $toMqttUser = MqttUser::findByUsername($to->email)->first();

        if (!$toMqttUser) {
            $fromMqttUser->username = $to->email;
            $fromMqttUser->save();
            return;
        }

        $existingTopics = MqttAcl::where('user_id', $toMqttUser->id)
            ->pluck('topic')
            ->toArray();

        MqttAcl::where('user_id', $fromMqttUser->id)
            ->whereNotIn('topic', $existingTopics)
            ->update(['user_id' => $toMqttUser->id]);

        MqttAcl::where('user_id', $fromMqttUser->id)->delete();

        $fromMqttUser->deactivate();
    }

    /**
     * Deletes all MQTT ACLs for the given user and deactivates their MQTT account.
     *
     * @param User $user User whose MQTT ACLs will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to MqttAcl.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        $mqttUser = MqttUser::findByUsername($user->email)->first();

        if (!$mqttUser) {
            return;
        }

        MqttAcl::where('user_id', $mqttUser->id)->delete();
        $mqttUser->deactivate();
    }
}
