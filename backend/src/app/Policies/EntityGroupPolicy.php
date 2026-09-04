<?php

namespace App\Policies;


use App\Models\Entity;
use App\Models\EntityGroup;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Repositories\EntityPermissionsRepository;
use App\Models\EntityPermissionType;

use App\Authorization\AppResourcePermission;
use App\Repositories\DeviceRepository;
use App\Authorization\AppPermission;
use App\Models\ResourceLimit;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;


class EntityGroupPolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the entity group.
     * 
     * @param User $user
     * @param EntityGroup $entityGroup
     */
    public function read(User $user, EntityGroup $entityGroup): Response
    {
        $can_read = $user->
            hasResourcePermissionTo(AppResourcePermission::READ, $entityGroup);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the entity group');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the entity group.
     * 
     * @param User $user
     * @param EntityGroup $entityGroup
     */
    public function update(User $user, EntityGroup $entityGroup): Response
    {
        $allowed_module = $user->can(AppPermission::DATA_SOURCES_ENTITIES_UPDATE->value);

        if (!$allowed_module) {
            return Response::deny('You are not allowed to modify entities');
        }

        $can_update = $user->
            hasResourcePermissionTo(AppResourcePermission::UPDATE, $entityGroup);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the entity group');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can delete the entity group.
     * 
     * @param User $user
     * @param EntityGroup $entityGroup
     */
    public function delete(User $user, EntityGroup $entityGroup): Response
    {
        return $this->update($user, $entityGroup);
    }

    /**
     * Checks if the user can create the entity group.
     * 
     * @param User $user
     * @param EntityGroup $entityGroup
     */
    public function create(User $user): Response
    {
        $allowed_module = $user->can(AppPermission::DATA_SOURCES_ENTITIES_UPDATE->value);

        ResourceLimitsHelper::canCreateOrFail($user, EntityGroup::class);

        if (!$allowed_module) {
            return Response::deny('You are not allowed to create entities');
        }

        return Response::allow();
    }


    /**
     * Checks if the user can list the entity groups.
     * 
     * @param User $user
     * @param EntityGroup $entityGroup
     */
    public function list(User $user): Response
    {

        return Response::allow();
    }

}