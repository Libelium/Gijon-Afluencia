<?php

namespace App\Policies;

use App\Authorization\AppResourcePermission;
use App\Repositories\DeviceRepository;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\Device;
use App\Models\User;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;

class DevicePolicy
{
    use HandlesAuthorization;

    private $userPolicy;

    public function __construct(UserPolicy $userPolicy)
    {
        $this->userPolicy = $userPolicy;
    }

    /**
     * Checks if the user can edit the device.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Device $device
     * @return void|bool
     */
    public function read(User $user, Device $device): Response
    {
        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $device);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the device');
        }

        return Response::allow();
    }


    /**
     * Checks if the user can update the device.
     * @param User $user
     * @param Device $device
     * @return bool|mixed
     */
    public function update(User $user, Device $device)
    {
        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $device);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the device');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the device.
     * @param User $user
     * @param Device $device
     * @return bool|mixed
     */
    public function delete(User $user)
    {
        $allowed = $user->can(AppPermission::APPLICATION_ADMIN->value);
        if (!$allowed) {
            return Response::deny('You are not allowed to delete devices');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create the device.
     * @param User $user
     * @param Device $device
     * @return bool|mixe
     */
    public function create(User $user): Response
    {
        $allowed = $user->can(AppPermission::DLM_IMPORTATION_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to create devices');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can list devices.
     *
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function list(User $user): Response
    {
        return Response::allow();
    }

    /**
     * Determine whether the user can list all devices.
     *
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function listAll(User $user): Response
    {
        $allowed = $user->can(AppPermission::ADMINISTRATION_VISUALIZER_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to list all devices');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can admin all application devices.
     *
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function admin(User $user): Response
    {
        $allowed = $user->can(AppPermission::APPLICATION_ADMIN->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to admin devices');
        }

        return Response::allow();
    }
}
