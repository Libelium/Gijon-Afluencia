<?php

namespace App\Policies;

use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Authorization\AppResourcePermission;
use App\Authorization\AppPermission;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;
use App\Providers\AppServiceProvider;
use Spatie\Permission\Contracts\Role;

class UserPolicy
{
    use HandlesAuthorization;

    /**
     * Perform pre-authorization checks.
     *
     * @param  \App\Models\User  $user
     * @param  string  $ability
     * @return void|bool
     */
    public function before(User $user, $ability)
    {
        if ($user->can(AppPermission::APPLICATION_ADMIN->value)) {
            return true;
        }
    }

    /**
     * Checks if the user can read the user.
     *
     * @param \App\Models\User $user
     * @param \App\Models\User $userToRead
     * @return bool
     */
    public function read(User $user, User $userToRead): Response
    {
        if ($user->id === $userToRead->id) {
            return Response::allow();
        }

        if ($userToRead->created_by && $user->id === $userToRead->created_by) {
            return Response::allow();
        }

        if ($user->isOrganizationAdmin() && $user->organization_id === $userToRead->organization_id) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to read this user\'s information.');
    }

    /**
     * Checks if the user can update the user.
     *
     * @param \App\Models\User $user
     * @param \App\Models\User $userToUpdate
     * @return bool
     */
    public function update(User $user, User $userToUpdate): Response
    {
        if ($user->id === $userToUpdate->id) {
            return Response::allow();
        }

        if ($userToUpdate->created_by && $user->id === $userToUpdate->created_by) {
            return Response::allow();
        }

        if ($user->isOrganizationAdmin() && $user->organization_id === $userToUpdate->organization_id) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to update this user.');
    }

    /**
     * Checks if the user can delete the user.
     *
     * @param \App\Models\User $user
     * @param \App\Models\User $userToDelete
     * @return bool
     */
    public function delete(User $user, User $userToDelete): Response
    {
        if ($user->id === $userToDelete->id) {
            return Response::deny('You cannot delete your own account.');
        }

        if ($userToDelete->created_by && $user->id === $userToDelete->created_by) {
            return Response::allow();
        }

        if ($user->isOrganizationAdmin() && $user->organization_id === $userToDelete->organization_id) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to delete this user.');
    }

    /**
     * Checks if the user has application admin permissions.
     *
     * @param \App\Models\User $user
     * @return bool
     */

    public function applicationAdmin(User $user): Response
    {
        $canReadApiKey = $user->can(AppPermission::APPLICATION_ADMIN->value);

        if (!$canReadApiKey) {
            return Response::deny('You are not the application admin');
        }

        return Response::allow();
    }

    /**
     * Checks if the user has importation permissions.
     *
     * @param \App\Models\User $user
     * @return bool
     */

    public function dlmImportation(User $user): Response
    {
        $canReadApiKey = $user->can(AppPermission::DLM_IMPORTATION_READ->value);

        if (!$canReadApiKey) {
            return Response::deny('You are not allowed to import data');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can block other user
     *
     * @param \App\Models\User $user
     * @param \App\Models\User $userToBlock
     * @return bool
     */

    public function block(User $user, User $userToBlock): Response
    {
        if ($user->id === $userToBlock->id) {
            return Response::deny('You are not allowed to block yourself');
        }

        if ($userToBlock->created_by && $user->id === $userToBlock->created_by && !$userToBlock->isOrganizationAdmin()) {
            return Response::allow();
        }

        if ($user->isOrganizationAdmin() && $user->organization_id === $userToBlock->organization_id && !$userToBlock->isOrganizationAdmin()) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to block this user.');
    }

    /**
     * Incidents moderation block. NOT same-org (staff and citizens live in
     * different orgs); instead strictly DESCENDING by incidents tier: admin > operator > citizen. So a
     * citizen blocks nobody, an operator blocks citizens, an admin blocks operators + citizens.
     * (APPLICATION_ADMIN bypasses via before(); block-reporter reach is also bounded by EntityPolicy@read.)
     */
    public function moderateBlock(User $user, User $target): Response
    {
        if ($user->organization_id !== $target->organization_id) {
            return Response::deny('You are not allowed to block users from other organizations.');
        }

        if ($user->id === $target->id) {
            return Response::deny('You cannot block yourself.');
        }

        if ($target->isOrganizationAdmin()) {
            return Response::deny('You cannot block an organization administrator.');
        }

        if ($this->incidentsTier($user) > $this->incidentsTier($target)) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to block this user.');
    }

    /**
     * Incidents account deletion. Always allows deleting one's OWN account. Never an org admin. (APPLICATION_ADMIN
     * bypasses via before(); IncidentsUserController does the operator team/intervention cleanup.)
     */
    public function moderateDelete(User $user, User $target): Response
    {
        if ($user->organization_id !== $target->organization_id) {
            return Response::deny('You are not allowed to delete users from other organizations.');
        }
        if ($user->id === $target->id) {
            return Response::allow();
        }

        if ($target->isOrganizationAdmin()) {
            return Response::deny('You cannot delete an organization administrator.');
        }

        if ($user->can(AppPermission::INCIDENTS_ADMIN->value)) {
            return Response::allow();
        }

        return Response::deny('You are not allowed to delete this user.');
    }

    /** Incidents-module tier of a user: 3 = admin, 2 = operator/reviewer, 1 = citizen/none. */
    private function incidentsTier(User $user): int
    {
        if ($user->can(AppPermission::INCIDENTS_ADMIN->value)) {
            return 3;
        }
        if ($user->can(AppPermission::INCIDENTS_REVIEW->value)) {
            return 2;
        }
        return 1;
    }

    /**
     * Determine whether the user can create a role
     *
     * @param \App\Models\User  $user
     * @param \Spatie\Permission\Models\Role  $role
     */
    public function create(User $user): Response
    {
        $allowed = $user->can(AppPermission::ROLES_UPDATE->value);

        ResourceLimitsHelper::canCreateOrFail($user, User::class);

        if (!$allowed) {
            return Response::deny('You are not allowed to create user');
        }

        return Response::allow();
    }

    /**
     * Determine whether the user can create OPERATOR (field-worker) users. This is the incidents-admin
     * ability (incidents.admin) that only allows creating users with the operator role — the
     * dedicated IncidentsUserController@store forces that role. Kept separate from create() so
     * granting it never widens general user management (roles.update).
     */
    public function createOperator(User $user): Response
    {
        $allowed = $user->can(AppPermission::INCIDENTS_ADMIN->value);

        ResourceLimitsHelper::canCreateOrFail($user, User::class);

        if (!$allowed) {
            return Response::deny('You are not allowed to create operator users');
        }

        return Response::allow();
    }
}
