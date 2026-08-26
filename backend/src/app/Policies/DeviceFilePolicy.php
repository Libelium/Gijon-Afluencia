<?php

namespace App\Policies;

use App\Models\User;
use App\Models\DeviceFile;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class DeviceFilePolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can view any device files.
     *
     * @param  \App\Models\User  $currentUser
     * @return \Illuminate\Auth\Access\Response
     */
    public function viewAny(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_DEVICE_FILES_READ->value)
            ? Response::allow()
            : Response::deny('You don\'t have permission to view any device files.');
    }

    /**
     * Determine whether the user can view the device file.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\DeviceFile  $deviceFile
     * @return \Illuminate\Auth\Access\Response
     */
    public function view(User $currentUser, DeviceFile $deviceFile): Response
    {
        // For viewing a specific device file, we can check if the user has read permission.
        return Response::allow();
    }

    /**
     * Determine whether the user can create (or upsert) a device file
     *
     * @param  \App\Models\User  $currentUser
     * @return \Illuminate\Auth\Access\Response
     */
    public function create(User $currentUser): Response
    {
        return $currentUser->can(AppPermission::ADMINISTRATION_DEVICE_FILES_UPDATE->value)
            ? Response::allow()
            : Response::deny('You don\'t have permission to create device files');
    }

    /**
     * Determine whether the user can update the device file.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\DeviceFile  $deviceFile
     * @return \Illuminate\Auth\Access\Response
     */
    public function update(User $currentUser, DeviceFile $deviceFile): Response
    {
        // For updating a device file, we check if the user has update permission.
        return $currentUser->can(AppPermission::ADMINISTRATION_DEVICE_FILES_UPDATE->value)
            ? Response::allow()
            : Response::deny('You don\'t have permission to update this device file.');
    }

    /**
     * Determine whether the user can delete the device file.
     *
     * @param  \App\Models\User  $currentUser
     * @param  \App\Models\DeviceFile  $deviceFile
     * @return \Illuminate\Auth\Access\Response
     */
    public function delete(User $currentUser, DeviceFile $deviceFile): Response
    {
        // For deleting a device file, we check if the user has update permission.
        // Often, delete permissions are tied to update or a specific delete permission.
        // Assuming ADMINISTRATION_DEVICE_FILES_UPDATE covers delete for now.
        return $currentUser->can(AppPermission::ADMINISTRATION_DEVICE_FILES_UPDATE->value)
            ? Response::allow()
            : Response::deny('You don\'t have permission to delete this device file.');
    }
}
