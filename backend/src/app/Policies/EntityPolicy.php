<?php

namespace App\Policies;


use App\Models\Entity;
use App\Models\User;
use App\Models\FiwareScope;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;
use App\Authorization\AppResourcePermission;

class EntityPolicy
{
    use HandlesAuthorization;

    private $scope_policy;

    public function __construct(FiwareScopePolicy $scope_policy)
    {
        $this->scope_policy = $scope_policy;
    }


    /**
     * Checks if the user can edit the entity.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Entity $entity
     * @return void|bool
     */
    public function read(User $user, Entity $entity): Response
    {
        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $entity);

        if ($can_read) {
            return Response::allow();
        }

        $entity = $entity->loadMissing('fiwareScope');

        return $this->scope_policy->read($user, $entity->fiwareScope);
    }

    /**
     * Checks if the user can update the entity.
     * @param User $user
     * @param Entity $entity
     * @return bool|mixed
     */
    public function update(User $user, Entity $entity)
    {
        if ($user->can(AppPermission::APPLICATION_ADMIN->value)) {
            return Response::allow();
        }

        $allowed = $user->can(AppPermission::DATA_SOURCES_ENTITIES_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to update entities');
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $entity);

        if ($can_update) {
            return Response::allow();
        }

        $entity = $entity->loadMissing('fiwareScope');

        return $this->scope_policy->update($user, $entity->fiwareScope);
    }

    public function uploadData(User $user, Entity $entity)
    {
        if ($user->can(AppPermission::DATA_SOURCES_ENTITIES_UPLOAD_DATA->value)) {
            // Check if the user also has read permission on the specific entity
            return $this->read($user, $entity);
        }

        return false;
    }

    public function uploadDataToEntity(User $user)
    {
        if ($user->can(AppPermission::DATA_SOURCES_ENTITIES_UPLOAD_DATA->value)) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to upload data to entities');
    }
}
