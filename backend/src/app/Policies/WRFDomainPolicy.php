<?php

namespace App\Policies;

use App\Authorization\AppPermission;
use App\Models\User;
use App\Models\WRFDomain;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;

class WRFDomainPolicy
{
    use HandlesAuthorization;

    public function viewAny(User $user): Response
    {
        return $user->can(AppPermission::WRF_SIMULATIONS_READ->value)
            ? Response::allow()
            : Response::deny('You are not allowed to view WRF domains.');
    }

    public function view(User $user, WRFDomain $domain): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_READ->value)) {
            return Response::deny('You are not allowed to view WRF domains.');
        }

        if ($user->organization->adminUser->id !== $domain->user_id) {
            return Response::deny('You are not allowed to view this WRF domain.');
        }

        return Response::allow();
    }

    public function create(User $user): Response
    {
        return $user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)
            ? Response::allow()
            : Response::deny('You are not allowed to create WRF domains.');
    }

    public function update(User $user, WRFDomain $domain): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)) {
            return Response::deny('You are not allowed to update WRF domains.');
        }

        if ($user->organization->adminUser->id !== $domain->user_id) {
            return Response::deny('You are not allowed to update this WRF domain.');
        }

        return Response::allow();
    }

    public function delete(User $user, WRFDomain $domain): Response
    {
        if (!$user->can(AppPermission::WRF_SIMULATIONS_UPDATE->value)) {
            return Response::deny('You are not allowed to delete WRF domains.');
        }

        if ($user->organization->adminUser->id !== $domain->user_id) {
            return Response::deny('You are not allowed to delete this WRF domain.');
        }

        return Response::allow();
    }
}
