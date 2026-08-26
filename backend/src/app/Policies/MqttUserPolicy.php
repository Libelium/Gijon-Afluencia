<?php

namespace App\Policies;

use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\MqttUser;
use App\Models\User;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;

class MqttUserPolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can list mqtt users.
     *
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function list(User $user): Response
    {
        $allowed = $user->can(AppPermission::ADMINISTRATION_APIKEYS_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to list mqtt users');
        }

        return Response::allow();
    }
}
