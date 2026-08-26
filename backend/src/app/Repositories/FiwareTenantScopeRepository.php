<?php

namespace App\Repositories;

use App\Models\FiwareTenant;
use App\Models\FiwareScope;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use App\Authorization\ResourcePermissionCache;
use App\Models\User;
class FiwareTenantScopeRepository
{
    public static function listPermittedTenants($userId, AppResourcePermission $permission)
    {
        $base_query = FiwareTenant::with('scopes');

        $base_query = $base_query->groupBy('fiware_tenants.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $base_query,
            $permission,
            $userId,
            FiwareTenant::class
        );

        return $query->get('fiware_tenants.*');
    }

    private static function updateScopeRequestWithPermissionCheck(
        object $query,
        int $userId,
        AppResourcePermission $permission
    ): object {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        $models = ResourcePermissionRepository::getUserModels(User::find($userId));

        $with_permission = $query->join(
            'model_has_resource_permissions',
            function ($join) use ($models, $permission_id) {
                $join->where('model_has_resource_permissions.resource_permission_id', $permission_id);

                $join->where(function ($query) use ($models) {
                    foreach ($models as $model) {
                        $query->orWhere(function ($q) use ($model) {
                            $q->where('model_has_resource_permissions.model_id', $model['model_id'])
                                ->where('model_has_resource_permissions.model_type', $model['model_type']);
                        });
                    }
                });

                $join->on(
                    function ($join) {
                        $join->on(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'fiware_scopes.fiware_tenant_id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareTenant())->getTable());
                            }
                        );

                        $join->orOn(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'fiware_scopes.id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareScope())->getTable());
                            }
                        );
                    }
                );
            }
        );

        return $with_permission;
    }

    private static function updateScopeRequestWithPermissionsCheck(
        object $query,
        int $userId,
        array $permission
    ): object {
        $permission_ids = [];
        foreach ($permission as $perm) {
            $permission_ids[] = app(ResourcePermissionCache::class)->getPermissionId($perm);
        }

        $models = ResourcePermissionRepository::getUserModels(User::find($userId));

        $with_permission = $query->join(
            'model_has_resource_permissions',
            function ($join) use ($models, $permission_ids) {
                $join->whereIn('model_has_resource_permissions.resource_permission_id', $permission_ids);

                $join->where(function ($query) use ($models) {
                    foreach ($models as $model) {
                        $query->orWhere(function ($q) use ($model) {
                            $q->where('model_has_resource_permissions.model_id', $model['model_id'])
                                ->where('model_has_resource_permissions.model_type', $model['model_type']);
                        });
                    }
                });

                $join->on(
                    function ($join) {
                        $join->on(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'fiware_scopes.fiware_tenant_id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareTenant())->getTable());
                            }
                        );

                        $join->orOn(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'fiware_scopes.id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareScope())->getTable());
                            }
                        );
                    }
                );
            }
        );

        return $with_permission;
    }

    public static function listPermittedScopes($userId, AppResourcePermission $permission)
    {
        $base_query = FiwareScope::with('tenant');

        $base_query = $base_query->groupBy('fiware_scopes.id');

        $query = self::updateScopeRequestWithPermissionCheck(
            $base_query,
            $userId,
            $permission,
            FiwareScope::class
        );

        return $query->get('fiware_scopes.*');
    }

    public static function listReadableTenants($userId)
    {
        return self::listPermittedTenants($userId, AppResourcePermission::READ);
    }

    /**
     * Retrieve scopes that the user has the specified permissions on,
     * optionally filtered by a search term across validated fields.
     *
     * @param int $userId
     * @param array $permissions
     * @param string|null $search
     * @param array $searchFields
     * @return \Illuminate\Database\Eloquent\Collection
     */
    public static function getScopesWithPermissions($userId, $permissions, $search = null, $searchFields = ['name'])
    {
        $base_query = FiwareScope::with('tenant');

        $base_query = $base_query->groupBy('fiware_scopes.id');

        $appPermissions = [];

        foreach ($permissions as $permission) {
            $appPermissions[] = AppResourcePermission::fromValue($permission);
        }

        $query = self::updateScopeRequestWithPermissionsCheck(
            $base_query,
            $userId,
            $appPermissions,
            FiwareScope::class
        );

        if ($search) {
            $query = $query->where(function ($query) use ($search, $searchFields) {
                foreach ($searchFields as $field) {
                    $query->orWhere($field, 'like', '%' . $search . '%');
                }
            });
        }

        return $query->select('fiware_scopes.id', 'fiware_scopes.name', 'fiware_scopes.fiware_tenant_id')->get();
    }

    public static function listUpdatableTenants($userId)
    {
        return self::listPermittedTenants($userId, AppResourcePermission::UPDATE);
    }

    public static function listReadableScopes($userId)
    {
        return self::listPermittedScopes($userId, AppResourcePermission::READ);
    }

    /**
     * Summary of createScope, and also the tenant if it does not exist
     * @param string $tenantName
     * @param string $scopeName
     * @return \App\Models\FiwareScope
     */
    public static function createScope(string $tenantName, string $scopeName): FiwareScope
    {
        $tenant = FiwareTenant::firstOrCreate(['name' => $tenantName]);
        if ($tenant->wasRecentlyCreated) {
            $tenant->updated_at = now();
            $tenant->created_at = now();
            $tenant->save();
        }

        $scope = FiwareScope::firstOrCreate([
            'name' => $scopeName,
            'fiware_tenant_id' => $tenant->id
        ]);

        if ($scope->wasRecentlyCreated) {
            $scope->updated_at = now();
            $scope->created_at = now();
            $scope->save();
        }

        $scope->tenant = $tenant;

        return $scope;
    }
}