<?php

namespace App\Policies;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\Workspace;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;

class WorkspacePolicy
{

    use HandlesAuthorization;

    /**
     * Checks if the user can read the workspace
     * @param \App\Models\User $user
     * @param \App\Models\Workspace $workspace
     * @return \Response
     */
    public function read(User $user, Workspace $workspace): Response
    {
        $allowed = $user->can(AppPermission::WORKSPACES_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to access the workspaces module');
        }

        $can_read = $user->hasResourcePermissionTo(AppResourcePermission::READ, $workspace);

        if (!$can_read) {
            return Response::deny('You are not allowed to read the workspace');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the workspace
     * @param \App\Models\User $user
     * @param \App\Models\Workspace $workspace
     * @return \Response
     */
    public function update(User $user, Workspace $workspace): Response
    {
        $allowed = $user->can(AppPermission::WORKSPACES_UPDATE->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to update the workspace module');
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $workspace);

        if (!$can_update) {
            return Response::deny('You are not allowed to update the workspace');
        }

        return Response::allow();
    }

    /**
     * Checks if the user can update the workspace
     * @param \App\Models\User $user
     * @param \App\Models\Workspace $workspace
     * @return \Response
     */
    public function updateUsers(User $user, Workspace $workspace)
    {
        $allowed = $user->can(AppPermission::WORKSPACES_UPDATE->value);

        if (!$allowed) {
            return false;
        }

        $can_update = $user->hasResourcePermissionTo(AppResourcePermission::UPDATE, $workspace);

        if (!$can_update) {
            return false;
        }

        return $workspace->user_id === $user->id;
    }

    /**
     * Checks if the user can delete the workspace. A user can delete a workspace
     * if they have the permission to update it.
     * @param \App\Models\User $user
     * @param \App\Models\Workspace $workspace
     * @return \Response
     */
    public function delete(User $user, Workspace $workspace): Response
    {
        return $this->update($user, $workspace) && $workspace->user_id === $user->id
            ? Response::allow()
            : Response::deny('Only the admin can delete the workspace');
    }

    /**
     * Checks if the user can create a new workspace.
     * @param \App\Models\User $user
     * @param \App\Models\Workspace $workspace
     * @return \Response
     */
    public function create(User $user): Response
    {
        $allowed = $user->hasAllPermissions([
            AppPermission::WORKSPACES_UPDATE->value,
        ]);

        ResourceLimitsHelper::canCreateOrFail($user, Workspace::class);

        if (!$allowed) {
            return Response::deny('You are not allowed to create workspaces');
        }

        return Response::allow();
    }

    /**
     * Determines if the user can list workspaces.
     * @param \App\Models\User $user
     * @return \Response
     */
    public function list(User $user): Response
    {
        $allowed = $user->can(AppPermission::WORKSPACES_READ->value);

        if (!$allowed) {
            return Response::deny('You are not allowed to access the workspaces module');
        }

        return Response::allow();
    }
}