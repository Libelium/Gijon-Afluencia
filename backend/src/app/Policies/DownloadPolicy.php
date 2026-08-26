<?php

namespace App\Policies;

use App\Repositories\PermissionRepository;

use App\Models\Download;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;

class DownloadPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can edit the entity.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Download $download
     * @return void|bool
     */
    public function read(User $user, Download $download): Response
    {
        $can_read = $user->hasResourcePermissionTo(
            AppResourcePermission::READ,
            $download
        );

        if (!$can_read) {
            return Response::deny('You are not allowed to read this download');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the entity.
     * @param User $user
     * @param Download $download
     * @return bool|mixed
     */
    public function update(User $user, Download $download)
    {
        $can_update = $user->hasResourcePermissionTo(
            AppResourcePermission::UPDATE,
            $download
        );

        if (!$can_update) {
            return Response::deny('You are not allowed to update this download');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the entity.
     * @param User $user
     * @param Download $download
     * @return bool|mixed
     */
    public function delete(User $user, Download $download)
    {
        return $this->update($user, $download);
    }
}
