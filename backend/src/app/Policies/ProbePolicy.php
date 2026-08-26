<?php

namespace App\Policies;

use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\Probe;
use App\Models\User;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;

class ProbePolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can edit the device.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Probe $device
     * @return void|bool
     */
    public function read(User $user, Probe $probe): Response
    {
        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $probe);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the probe');
        }

        return Response::allow();
    }


    /**
     * Checks if the user can update the probe.
     * @param User $user
     * @param Probe $probe
     * @return bool|mixed
     */
    public function update(User $user, Probe $probe)
    {
        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $probe);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the probe');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the probe.
     * @param User $user
     * @param Probe $probe
     * @return bool|mixed
     */
    public function delete(User $user, Probe $probe)
    {
        return $this->update($user, $probe);
    }

    /**
     * Checks if the user can create the probe.
     * @param User $user
     * @param Probe $probe
     * @return bool|mixed
     */
    public function create(User $user): Response
    {
        $allowed = $user->can(AppPermission::DLM_IMPORTATION_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to create probes');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can list probes.
     * 
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function list(User $user): Response
    {
        return Response::allow();
    }
}
