<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use App\Models\Regulation;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Models\OutConnectors\OutConnector;
use App\Models\ResourceLimit;
use App\Helpers\ResourceLimitsHelper;

class OutConnectorPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the out connector.
     * 
     * @param User $user
     * @param OutConnector $outConnector
     */
    public function read(User $user, OutConnector $outConnector): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_READ->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to read out connectors');
        }

        $can_read_out_connector = $user->hasResourcePermissionTo(AppResourcePermission::READ, $outConnector);

        if (!$can_read_out_connector) {
            return Response::deny('You are not allowed to read this out connector');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the out connector.
     * 
     * @param User $user
     * @param OutConnector $outConnector
     */
    public function update(User $user, OutConnector $outConnector): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_UPDATE->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to update out connectors');
        }

        $can_update_out_connector = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $outConnector);

        if (!$can_update_out_connector) {
            return Response::deny('You are not allowed to update this out connector');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can list out connectors.
     * 
     * @param \App\Models\User $user
     * @return \Illuminate\Auth\Access\Response
     */
    public function list(User $user): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_READ->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to read out connectors');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the out connector.
     * 
     * @param User $user
     * @param OutConnector $outConnector
     */
    public function delete(User $user, OutConnector $outConnector): Response
    {
        return $this->update($user, $outConnector);
    }

    /**
     * Checks if the user can create an out connector.
     * 
     * @param User $user
     */
    public function create(User $user): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_UPDATE->value);

        ResourceLimitsHelper::canCreateOrFail($user, OutConnector::class);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to create out connectors');
        }

        return Response::allow();
    }
}