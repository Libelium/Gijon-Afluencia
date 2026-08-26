<?php

namespace App\Repositories;

use App\Models\Permission;

class PermissionRepository
{
    /**
     * @param int|null $userId
     * @param int|null $projectableId
     * @param string|null $permission
     * @return mixed
     */
    public static function hasPermission(int $userId = null, int $projectableId = null, string $permission = null)
    {
        $model = [
            'devices' => 'App\Models\Device',
            'dashboards' => 'App\Models\Dash'
        ];

        $modelKey = explode('.', $permission)[0];

        $hasPermission = Permission::join('role_has_permissions', 'permissions.id', '=', 'role_has_permissions.permission_id')
            ->join('roles', 'role_has_permissions.role_id', '=', 'roles.id')
            ->join('model_has_roles', 'roles.id', '=', 'model_has_roles.role_id')
            ->join('project_users', 'model_has_roles.model_id', '=', 'project_users.id')
            ->join('projects', 'project_users.project_id', '=', 'projects.id')
            ->join('projectables', 'projects.id', '=', 'projectables.project_id')

            ->where('projectables.projectable_type', $model[$modelKey])
            ->where('projectables.projectable_id', $projectableId)
            ->where('project_users.user_id', $userId)
            ->where('model_has_roles.model_type', 'App\Models\ProjectUser')
            ->where('permissions.name', $permission)

            ->count();

        return $hasPermission > 0;
    }

    /**
     * Get the permisison from a model for the user
     */
    public static function getPermission(int $userId, int $projectableId, string $model): Permission
    {
        $availableModel = [
            'devices' => 'App\Models\Device',
            'dashboards' => 'App\Models\Dash'
        ];

        $permission = Permission::select('permissions.name')
            ->join('role_has_permissions', 'permissions.id', '=', 'role_has_permissions.permission_id')
            ->join('roles', 'role_has_permissions.role_id', '=', 'roles.id')
            ->join('model_has_roles', 'roles.id', '=', 'model_has_roles.role_id')
            ->join('project_users', 'model_has_roles.model_id', '=', 'project_users.id')
            ->join('projects', 'project_users.project_id', '=', 'projects.id')
            ->join('projectables', 'projects.id', '=', 'projectables.project_id')
            ->where('projectables.projectable_type', $availableModel[$model])
            ->where('projectables.projectable_id', $projectableId)
            ->where('project_users.user_id', $userId)
            ->where('model_has_roles.model_type', 'App\Models\ProjectUser')
            ->first();
        return $permission;
    }

    /**
     * To check if user has the received project permission
     */
    public static function hasProjectPermission(int $userId, int $projectId, string $permission): bool
    {
        $hasPermission = Permission::join('role_has_permissions', 'permissions.id', '=', 'role_has_permissions.permission_id')
            ->join('roles', 'role_has_permissions.role_id', '=', 'roles.id')
            ->join('model_has_roles', 'roles.id', '=', 'model_has_roles.role_id')
            ->join('project_users', 'model_has_roles.model_id', '=', 'project_users.id')
            ->join('projects', 'project_users.project_id', '=', 'projects.id')
            ->where('projects.id', $projectId)
            ->where('project_users.user_id', $userId)
            ->where('model_has_roles.model_type', 'App\Models\ProjectUser')
            ->where('permissions.name', $permission)
            ->count();
        return $hasPermission > 0;
    }

    /**
     * Get the permisison from a model for the user
     */
    public static function getProjectPermission(int $userId, int $projectId, string $resource): Permission
    {
        $types = [
            "dash" => "project_dashboards",
            "device" => "project_devices"
        ];

        $permission = Permission::select('permissions.name')
            ->join('role_has_permissions', 'permissions.id', '=', 'role_has_permissions.permission_id')
            ->join('roles', 'role_has_permissions.role_id', '=', 'roles.id')
            ->join('model_has_roles', 'roles.id', '=', 'model_has_roles.role_id')
            ->join('project_users', 'model_has_roles.model_id', '=', 'project_users.id')
            ->join('projects', 'project_users.project_id', '=', 'projects.id')
            ->where('projects.id', $projectId)
            ->where('project_users.user_id', $userId)
            ->where('model_has_roles.model_type', 'App\Models\ProjectUser')
            ->where('permissions.name', 'like', $types[$resource].'%')
            ->first();

        return $permission;
    }
}
