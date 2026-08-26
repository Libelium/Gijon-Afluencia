<?php

namespace App\Policies;

use App;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Models\User;
use Spatie\Permission\Models\Role;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Auth\Access\Response;
use App\Models\Organization;

class OrganizationPolicy
{
    use HandlesAuthorization;

    private $userPolicy;

    public function __construct(UserPolicy $userPolicy)
    {
        $this->userPolicy = $userPolicy;
    }

    /**
     * Determine whether the user can view the organization.
     *
     * @param  \App\Models\User  $user
     * @param  \App\Models\Organization  $organization
     * @return mixed
     */
    public function read(User $user, Organization $organization)
    {
        $can_read = $user->can(AppPermission::ORGANIZATIONS_READ->value);

        if (!$can_read) {
            return Response::deny('You are not allowed to read organizations');
        }

        $same_organization = $organization->id === $user->organization_id;

        if ($same_organization) {
            return Response::allow();
        }

        $is_admin = $user->can(AppPermission::ADMINISTRATION_READ->value);

        if ($is_admin) {
            return Response::allow();
        }

        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $organization);

        if (!$can_read) {
            return Response::deny('You are not allowed to read this organization');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can view the organization.
     *
     * @param  \App\Models\User  $user
     * @param  \App\Models\Organization  $organization
     * @return mixed
     */
    public function count(User $user, Organization $organization)
    {
        $same_organization = $organization->id === $user->organization_id;

        if ($same_organization) {
            return Response::allow();
        }

        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $organization);

        if (!$can_read) {
            return Response::deny('You are not allowed to read this organization');
        }

        return Response::allow();
    }

    public function update(User $user, Organization $organization)
    {
        $can_update = $user->can(AppPermission::ORGANIZATIONS_UPDATE->value);

        if (!$can_update) {
            return Response::deny('You are not allowed to update organizations');
        }

        $same_organization = $organization->id === $user->organization_id;

        if ($same_organization) {
            return Response::allow();
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $organization);

        if (!$can_update) {
            return Response::deny('You are not allowed to update this organization');
        }

        return Response::allow();
    }

    public function resellerRead(User $user, Organization $organization): Response
    {
        if (!$user->can(AppPermission::RESELLER_READ->value)) {
            return Response::deny('You are not a reseller');
        }

        // Reuse the organization access logic.
        return $this->read($user, $organization);
    }

    public function resellerUpdate(User $user, Organization $organization): Response
    {
        if (!$user->can(AppPermission::RESELLER_UPDATE->value)) {
            return Response::deny('You are not a reseller');
        }

        return $this->update($user, $organization);
    }

    /**
     * Determine whether the user can create organizations. This requires admin permissions.
     * 
     * @param User $user
     * @return bool
     */
    public function create(User $user)
    {
        return $this->userPolicy->applicationAdmin($user);
    }

    /**
     * Determine whether the user can paginate organizations.
     * 
     * @param User $user
     * @return bool
     */
    public function paginate(User $user)
    {
        $permissions = [
            AppPermission::ADMINISTRATION_MOSQUITTO_USERS_READ,
            AppPermission::ADMINISTRATION_IMPERSONATION_READ,
            AppPermission::ADMINISTRATION_APIKEYS_READ,
            AppPermission::ADMINISTRATION_FIWARE_SUBSCRIPTIONS_READ,
            AppPermission::ADMINISTRATION_FIWARE_SUBSCRIPTIONS_UPDATE,
            AppPermission::ADMINISTRATION_RESOURCE_LIMITS_READ,
            AppPermission::ADMINISTRATION_RESOURCE_LIMITS_UPDATE,
            AppPermission::ADMINISTRATION_DEVICE_FILES_READ,
            AppPermission::ADMINISTRATION_DEVICE_FILES_UPDATE,
            AppPermission::ADMINISTRATION_VISUALIZER_READ,
            AppPermission::ADMINISTRATION_VISUALIZER_UPDATE,
            AppPermission::ADMINISTRATION_HEALTHCHECKS_READ,

        ];

        return $user->hasAnyPermission($permissions);
    }
}
