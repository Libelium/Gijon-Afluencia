<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use App\Models\User;
use App\Models\WRFSimulation;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class WRFSimulationPolicy
{
    use HandlesAuthorization;

    public function viewAny(User $user): Response
    {
        return $user->can(AppPermission::WRF_SIMULATIONS_READ->value)
            ? Response::allow()
            : Response::deny('You are not allowed to view WRF simulations.');
    }

    public function view(User $user, WRFSimulation $simulation): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_READ->value)) {
            return Response::deny('You are not allowed to view WRF simulations.');
        }

        if ($user->organization->adminUser->id !== $simulation->domain->user_id) {
            return Response::deny('You are not allowed to view this WRF simulation.');
        }

        return Response::allow();
    }

    public function create(User $user): Response
    {
        return $user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)
            ? Response::allow()
            : Response::deny('You are not allowed to create WRF simulations.');
    }

    public function update(User $user, WRFSimulation $simulation): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)) {
            return Response::deny('You are not allowed to update WRF simulations.');
        }

        if ($user->organization->adminUser->id !== $simulation->domain->user_id) {
            return Response::deny('You are not allowed to update this WRF simulation.');
        }

        return Response::allow();
    }

    public function delete(User $user, WRFSimulation $simulation): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)) {
            return Response::deny('You are not allowed to delete WRF simulations.');
        }

        if ($user->organization->adminUser->id !== $simulation->domain->user_id) {
            return Response::deny('You are not allowed to delete this WRF simulation.');
        }

        return Response::allow();
    }
}
