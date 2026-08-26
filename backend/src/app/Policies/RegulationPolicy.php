<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use App\Models\Regulation;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;

class RegulationPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the regulation.
     * 
     * @param User $user
     * @param
     * @return Response
     */
    public function read(User $user, Regulation $regulation): Response
    {
        $can_regulations = $user->can(AppPermission::DASHBOARDS_READ->value);

        if (!$can_regulations) {
            return Response::deny('You are not allowed to read regulations');
        }

        $can_read_regulation = $user->hasResourcePermissionTo(AppResourcePermission::READ, $regulation);

        if (!$can_read_regulation) {
            return Response::deny('You are not allowed to read this regulation');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the regulation.
     * 
     * @param User $user
     * @return Response
     */
    public function update(User $user, Regulation $regulation): Response
    {
        $can_regulations = $user->can(AppPermission::DASHBOARDS_UPDATE->value);

        if (!$can_regulations) {
            return Response::deny('You are not allowed to update regulations');
        }

        $can_update_regulation = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $regulation);

        if (!$can_update_regulation) {
            return Response::deny('You are not allowed to update this regulation');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the regulation.
     * 
     * @param User $user
     * @return Response
     */
    public function delete(User $user, Regulation $regulation): Response
    {
        $can_regulations = $user->can(AppPermission::DASHBOARDS_UPDATE->value);

        if (!$can_regulations) {
            return Response::deny('You are not allowed to delete regulations');
        }

        $can_delete_regulation = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $regulation);

        if (!$can_delete_regulation) {
            return Response::deny('You are not allowed to delete this regulation');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can create the regulation.
     * 
     * @param User $user
     * @return Response
     */
    public function create(User $user): Response
    {
        $can_regulations = $user->can(AppPermission::DASHBOARDS_UPDATE->value);

        if (!$can_regulations) {
            return Response::deny('You are not allowed to create regulations');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can list the regulations.
     * 
     * @param User $user
     * @return Response
     */
    public function list(User $user): Response
    {
        $can_regulations = $user->can(AppPermission::DASHBOARDS_READ->value);

        if (!$can_regulations) {
            return Response::deny('You are not allowed to list regulations');
        }

        return Response::allow();
    }
}
