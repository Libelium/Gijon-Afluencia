<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class BackgroundJobPolicy
{
    use HandlesAuthorization;

    public function list(User $user): Response
    {
        return $user->can(AppPermission::BACKGROUND_JOBS_READ->value)
            ? Response::allow()
            : Response::deny('You are not allowed to access background jobs');
    }

}
