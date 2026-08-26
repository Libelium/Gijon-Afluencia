<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\OutConnectors\MappingSchema;
use Illuminate\Auth\Access\Response;

class MappingSchemaPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the out connector.
     * 
     * @param User $user
     * @param MappingSchema $MappingSchema
     */
    public function read(User $user, MappingSchema $MappingSchema): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_READ->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to read out connectors (neither mapping schemas)');
        }

        $can_read_map = $user->hasResourcePermissionTo(AppResourcePermission::READ, $MappingSchema);

        if (!$can_read_map) {
            return Response::deny('You are not allowed to read this mapping schema');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the out connector.
     * 
     * @param User $user
     * @param OutConnector $outConnector
     */
    public function update(User $user, MappingSchema $MappingSchema): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_READ->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to read out connectors (neither mapping schemas)');
        }

        $can_update_map = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $MappingSchema);

        if (!$can_update_map) {
            return Response::deny('You are not allowed to read this mapping schema');
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
            return Response::deny('You are not allowed to read out connectors (neither mapping schemas)');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the out connector.
     * 
     * @param User $user
     * @param OutConnector $outConnector
     */
    public function delete(User $user, MappingSchema $MappingSchema): Response
    {
        return $this->update($user, $MappingSchema);
    }

    /**
     * Checks if the user can create an out connector.
     * 
     * @param User $user
     */
    public function create(User $user): Response
    {
        $can_out_connectors = $user->can(AppPermission::OUT_CONNECTORS_UPDATE->value);

        if (!$can_out_connectors) {
            return Response::deny('You are not allowed to create out connectors (neither mapping schemas)');
        }

        return Response::allow();
    }
}
