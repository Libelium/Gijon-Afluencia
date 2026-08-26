<?php

namespace App\Policies;
use App\Authorization\AppPermission;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class BootstrapPolicy
{

    use HandlesAuthorization;

    /**
     * Checks if the user can create a new bootstrap profile.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function create(User $user): Response
    {
        $allowed = $user->hasAllPermissions([
            AppPermission::BOOTSTRAP_UPDATE->value,
            AppPermission::BOOTSTRAP_READ->value,
        ]);

        if (!$allowed) {
            return Response::deny('You are not allowed to create a profile in the bootstrap module.');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update a bootstrap profile.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function update(User $user): Response
    {
        $allowed = $user->hasAllPermissions([
            AppPermission::BOOTSTRAP_UPDATE->value,
            AppPermission::BOOTSTRAP_READ->value,
        ]);

        if (!$allowed) {
            return Response::deny('You are not allowed to update a profile in the bootstrap module.');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete a bootstrap profile.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function delete(User $user): Response
    {
        $allowed = $user->hasAllPermissions([
            AppPermission::BOOTSTRAP_UPDATE->value,
            AppPermission::BOOTSTRAP_READ->value,
        ]);

        if (!$allowed) {
            return Response::deny('You are not allowed to delete a profile in the bootstrap module.');
        }

        return Response::allow();
    }

    /**
     * Determines if the user can list device manager bootstrap stuff.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function list(User $user): Response
    {
        $allowed = $user->can(AppPermission::BOOTSTRAP_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to access the bootstrap module');
        }

        return Response::allow();
    }
}