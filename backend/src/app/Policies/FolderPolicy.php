<?php

namespace App\Policies;

use App\Models\Folder;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;

class FolderPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the folder.
     */
    public function read(User $user, Folder $folder): Response
    {
        if (!$user->can(AppPermission::ANALYTICS_READ->value)) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        if (!$user->can(AppPermission::REPORTS_READ->value)) {
            return Response::deny('You are not allowed to read reports');
        }

        if (!$user->hasResourcePermissionTo(AppResourcePermission::READ, $folder)) {
            return Response::deny('You are not allowed to read this folder');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create folders.
     */
    public function create(User $user): Response
    {
        if (!$user->can(AppPermission::ANALYTICS_READ->value)) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        if (!$user->can(AppPermission::REPORTS_UPDATE->value)) {
            return Response::deny('You are not allowed to update reports');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the folder.
     */
    public function update(User $user, Folder $folder): Response
    {
        if (!$user->can(AppPermission::ANALYTICS_READ->value)) {
            return Response::deny('You are not allowed to read the analytics module');
        }

        if (!$user->can(AppPermission::REPORTS_UPDATE->value)) {
            return Response::deny('You are not allowed to update reports');
        }

        if (!$user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $folder)) {
            return Response::deny('You are not allowed to update this folder');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the folder.
     */
    public function delete(User $user, Folder $folder)
    {
        return $this->update($user, $folder);
    }
}
