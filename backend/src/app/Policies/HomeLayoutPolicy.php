<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use App\Helpers\ResourceLimitsHelper;
use App\Models\HomeLayout;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class HomeLayoutPolicy
{
    use HandlesAuthorization;

    public function read(User $user, HomeLayout $homeLayout): Response
    {
        if ($user->id !== $homeLayout->user_id) {
            return Response::deny('You are not allowed to read this layout');
        }

        return Response::allow();
    }

    public function update(User $user, HomeLayout $homeLayout): Response
    {
        $allowed = $user->organization->adminUser->can(AppPermission::HOME_LAYOUTS_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to update home layouts');
        }

        if ($user->id !== $homeLayout->user_id) {
            return Response::deny('You are not allowed to update this layout');
        }

        return Response::allow();
    }

    public function delete(User $user, HomeLayout $homeLayout): Response
    {
        return $this->update($user, $homeLayout);
    }

    public function create(User $user): Response
    {
        $allowed = $user->organization->adminUser->can(AppPermission::HOME_LAYOUTS_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to create home layouts');
        }

        ResourceLimitsHelper::canCreateOrFail($user, HomeLayout::class);

        return Response::allow();
    }

    public function list(User $user): Response
    {
        return Response::allow();
    }
}
