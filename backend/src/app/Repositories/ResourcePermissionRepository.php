<?php

namespace App\Repositories;

use App\Authorization\AppResourcePermission;
use App\Models\Authorization\ModelHasResourcePermission;
use Illuminate\Database\Eloquent\Model;
use App\Authorization\ResourcePermissionCache;
use App\Models\Entity;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Organization;
use Illuminate\Support\Collection;
use App\Models\User;
use Illuminate\Support\Facades\Auth;
use Illuminate\Database\Eloquent\Builder;
use App\Services\SearchFieldValidator;


class ResourcePermissionRepository
{
    public static function updateModelsQueryWithPermissionCheck(
        object $query,
        AppResourcePermission $permission,
        array $models,
        $modelClass,
        bool $polymorphicJoin = false
    ): object {

        $resourceTableName = (new $modelClass)->getTable();

        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        return $query->join(
            'model_has_resource_permissions',
            function ($join) use (
                $models,
                $permission_id,
                $resourceTableName,
                $polymorphicJoin
            ) {

                if ($polymorphicJoin) {

                    $join->on(
                        'model_has_resource_permissions.resource_id',
                        '=',
                        $resourceTableName . '.resource_id'
                    )
                        ->on(
                            'model_has_resource_permissions.resource_type',
                            '=',
                            $resourceTableName . '.resource_type'
                        );
                } else {

                    $join->on(
                        'model_has_resource_permissions.resource_id',
                        '=',
                        $resourceTableName . '.id'
                    )
                        ->where('model_has_resource_permissions.resource_type', $resourceTableName);
                }

                $join->where('model_has_resource_permissions.resource_permission_id', $permission_id);

                // Group models by type and use whereIn for efficiency
                $modelsByType = [];
                foreach ($models as $model) {
                    $modelsByType[$model['model_type']][] = $model['model_id'];
                }

                $join->where(function ($query) use ($modelsByType) {
                    foreach ($modelsByType as $modelType => $modelIds) {
                        $query->orWhere(function ($q) use ($modelType, $modelIds) {
                            $q->where('model_has_resource_permissions.model_type', $modelType)
                                ->whereIn('model_has_resource_permissions.model_id', $modelIds);
                        });
                    }
                });
            }
        );
    }

    public static function getUserModels(
        User $user
    ): array {
        return [
            [
                'model_id' => $user->id,
                'model_type' => $user->getTable()
            ]
        ];
    }

    public static function updateQueryWithPermissionCheck(
        object $query,
        AppResourcePermission $permission,
        int $userId,
        $modelClass,
        bool $polymorphicJoin = false
    ): object {
        $models = ResourcePermissionRepository::getUserModels(User::find($userId));

        return ResourcePermissionRepository::updateModelsQueryWithPermissionCheck(
            $query,
            $permission,
            $models,
            $modelClass,
            $polymorphicJoin
        );
    }


    public static function deleteAllPermissionsForResource(Model $model): void
    {
        ModelHasResourcePermission::where('resource_id', $model->id)
            ->where('resource_type', $model->getTable())
            ->delete();
    }

    public static function getPermissionIds(array $permissions): Collection
    {
        return collect($permissions)->map(
            function ($permission) {
                return app(ResourcePermissionCache::class)->getPermissionId($permission);
            }
        );
    }

    public static function toAppPermission(int $permission_id): AppResourcePermission
    {
        return AppResourcePermission::fromValue(
            app(ResourcePermissionCache::class)->getPermissionName($permission_id)
        );
    }

    public static function ModelHasResourcePermission(Model $source_model, AppResourcePermission $permission, Model $model)
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        return ModelHasResourcePermission::where(
            [
                'resource_permission_id' => $permission_id,
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->where(function ($query) use ($source_model) {
            $query->orWhere(function ($q) use ($source_model) {
                $q->where('model_id', $source_model['model_id'])
                    ->where('model_type', $source_model['model_type']);
            });
        })
            ->exists();
    }

    public static function UserHasResourcePermissionTo(User $user, AppResourcePermission $permission, Model $model): bool
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        $models = ResourcePermissionRepository::getUserModels($user);

        return ModelHasResourcePermission::where(
            [
                'resource_permission_id' => $permission_id,
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->where(function ($query) use ($models, $model) {
            foreach ($models as $model) {
                $query->orWhere(function ($q) use ($model) {
                    $q->where('model_id', $model['model_id'])
                        ->where('model_type', $model['model_type']);
                });
            }
        })
            ->exists();
    }

    public static function ModelHasResourcePermissionToModel(Model $source_model, AppResourcePermission $permission, $model_type, $model_id)
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        return ModelHasResourcePermission::where(
            [
                'resource_permission_id' => $permission_id,
                'resource_type' => $model_type,
                'resource_id' => $model_id,
            ]
        )->where(function ($query) use ($source_model) {
            $query->orWhere(function ($q) use ($source_model) {
                $q->where('model_id', $source_model['model_id'])
                    ->where('model_type', $source_model['model_type']);
            });
        })
            ->exists();
    }

    public static function UserHasResourcePermissionToModel(User $user, AppResourcePermission $permission, $model_type, $model_id)
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        $models = ResourcePermissionRepository::getUserModels($user);

        return ModelHasResourcePermission::where(
            [
                'resource_permission_id' => $permission_id,
                'resource_type' => $model_type,
                'resource_id' => $model_id,
            ]
        )->where(function ($query) use ($models) {
            foreach ($models as $model) {
                $query->orWhere(function ($q) use ($model) {
                    $q->where('model_id', $model['model_id'])
                        ->where('model_type', $model['model_type']);
                });
            }
        })
            ->exists();
    }



    public static function userHasResourcePermissionToModelsBulk(
        array $userModels,
        int $permissionId,
        string $modelType,
        array $modelIds
    ): array {
        if (empty($modelIds) || empty($userModels)) {
            return [];
        }

        $q = ModelHasResourcePermission::query()
            ->select('resource_id')
            ->where('resource_permission_id', $permissionId)
            ->where('resource_type', $modelType)
            ->whereIn('resource_id', array_values(array_unique($modelIds)))
            ->where(function (Builder $query) use ($userModels) {
                foreach ($userModels as $m) {
                    $query->orWhere(function ($qq) use ($m) {
                        $qq->where('model_id', $m['model_id'])
                            ->where('model_type', $m['model_type']);
                    });
                }
            })
            ->groupBy('resource_id');

        return $q->pluck('resource_id')->all();
    }

    /**
     * Bulk read-permission check for entities, mirroring EntityPolicy::read() cascade:
     * entity-level → tenant-level → scope-level.
     *
     * Entities not found in the database are considered authorized.
     * Returns the URNs the user is NOT allowed to read (empty array = all authorized).
     * Single query: NOT EXISTS short-circuits on first matching permission per entity.
     */
    public static function getUnauthorizedEntityUrns(User $user, array $urns, int $scopeId): array
    {
        if (empty($urns)) {
            return [];
        }

        $permissionId = app(ResourcePermissionCache::class)->getPermissionId(AppResourcePermission::READ);
        $userModels   = self::getUserModels($user);

        $entityTable = (new Entity)->getTable();
        $scopeTable  = (new FiwareScope)->getTable();
        $tenantTable = (new FiwareTenant)->getTable();

        // Outer query: candidate entities in this scope that match the requested URNs.
        // JOIN fiware_scopes to expose fiware_tenant_id for the correlated subquery below.
        // Entities not found here are absent from the result, so they are implicitly authorized.
        return Entity::where('entities.fiware_scope_id', $scopeId)
            ->whereIn('entities.urn', $urns)
            ->join('fiware_scopes', 'fiware_scopes.id', '=', 'entities.fiware_scope_id')
            // Keep only entities for which NO matching permission row exists.
            // NOT EXISTS short-circuits per entity: stops scanning as soon as one grant is found.
            ->whereNotExists(function ($sub) use ($permissionId, $userModels, $entityTable, $scopeTable, $tenantTable) {
                $sub->selectRaw('1')
                    ->from('model_has_resource_permissions')
                    // Must be a READ permission.
                    ->where('resource_permission_id', $permissionId)
                    // Permission cascade: a grant at any of the three levels is sufficient.
                    ->where(function ($q) use ($entityTable, $scopeTable, $tenantTable) {
                        // Level 1 — direct permission on the entity itself.
                        $q->orWhere(function ($q) use ($entityTable) {
                            $q->where('resource_type', $entityTable)
                              ->whereColumn('resource_id', 'entities.id');
                        // Level 2 — permission on the parent tenant (broadest grant).
                        })->orWhere(function ($q) use ($tenantTable) {
                            $q->where('resource_type', $tenantTable)
                              ->whereColumn('resource_id', 'fiware_scopes.fiware_tenant_id');
                        // Level 3 — permission on the parent scope.
                        })->orWhere(function ($q) use ($scopeTable) {
                            $q->where('resource_type', $scopeTable)
                              ->whereColumn('resource_id', 'entities.fiware_scope_id');
                        });
                    })
                    // Grant must belong to the user.
                    ->where(function ($q) use ($userModels) {
                        foreach ($userModels as $m) {
                            $q->orWhere(function ($qq) use ($m) {
                                $qq->where('model_id', $m['model_id'])
                                   ->where('model_type', $m['model_type']);
                            });
                        }
                    });
            })
            ->pluck('entities.urn')
            ->all();
    }

    public static function giveUserResourcePermissionTo(User $user, AppResourcePermission $permission, Model $model): ModelHasResourcePermission
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        $attributes = [
            'model_id' => $user->id,
            'model_type' => $user->getTable(),
            'resource_permission_id' => $permission_id,
            'resource_type' => $model->getTable(),
            'resource_id' => $model->id,
        ];

        $now = now();
        ModelHasResourcePermission::upsert(
            [array_merge($attributes, ['created_at' => $now, 'updated_at' => $now])],
            array_keys($attributes),
            ['updated_at']
        );

        return ModelHasResourcePermission::where($attributes)->first();
    }

    public static function giveUserResourcePermissionsTo(User $user, array $permissions, Model $model): array
    {
        $rp_ids = ResourcePermissionRepository::getPermissionIds($permissions);
        $now = now();

        $records = $rp_ids->map(function ($rp_id) use ($model, $user, $now) {
            return [
                'model_id' => $user->id,
                'model_type' => $user->getTable(),
                'resource_permission_id' => $rp_id,
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
                'created_at' => $now,
                'updated_at' => $now,
            ];
        })->all();

        ModelHasResourcePermission::upsert(
            self::deduplicateRecords($records),
            ['model_id', 'model_type', 'resource_permission_id', 'resource_type', 'resource_id'],
            ['updated_at']
        );

        return $records;
    }

    public static function revokeUserResourcePermissionTo(User $user, AppResourcePermission $permission, Model $model)
    {
        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        ModelHasResourcePermission::where(
            [
                'model_id' => $user->id,
                'model_type' => $user->getTable(),
                'resource_permission_id' => $permission_id,
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->delete();
    }

    public static function revokeUserResourcePermissionsTo(User $user, array $permissions, Model $model)
    {
        $rp_ids = ResourcePermissionRepository::getPermissionIds($permissions);

        ModelHasResourcePermission::where(
            [
                'model_id' => $user->id,
                'model_type' => $user->getTable(),
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->whereIn('resource_permission_id', $rp_ids)->delete();
    }

    public static function getUserResourcePermissionsForDevice(User $user, Model $model): array
    {
        $models = ResourcePermissionRepository::getUserModels($user);

        $user_has_resources = ModelHasResourcePermission::where(
            [
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->where(function ($query) use ($models, $model) {
            foreach ($models as $model) {
                $query->orWhere(function ($q) use ($model) {
                    $q->where('model_id', $model['model_id'])
                        ->where('model_type', $model['model_type']);
                });
            }
        })->get();

        return $user_has_resources->map(
            function ($permission) {
                return ResourcePermissionRepository::toAppPermission(
                    $permission->resource_permission_id
                );
            }
        )->all();
    }


    public static function getUserResourcePermissions(User $user, Model $model): Collection
    {
        $models = ResourcePermissionRepository::getUserModels($user);
        $permissions = ModelHasResourcePermission::where(
            [
                'resource_type' => $model->getTable(),
                'resource_id' => $model->id,
            ]
        )->where(function ($query) use ($models, $model) {
            foreach ($models as $model) {
                $query->orWhere(function ($q) use ($model) {
                    $q->where('model_id', $model['model_id'])
                        ->where('model_type', $model['model_type']);
                });
            }
        })->with('resource_permission')->get();

        return $permissions->map(
            function ($permission) use ($model) {
                return [
                    'resource' => $model->getTable() . '.' . $permission->resource_id,
                    'action' => $permission->resource_permission->name,
                ];
            }
        );
    }


    /**
     * Retrieve all resources of a given type that the user has the specified permissions on,
     * optionally filtered by a search term across validated fields.
     *
     * @param User $user
     * @param array $permission
     * @param string $resource_type
     * @param string|null $search
     * @param array $search_fields
     * @return Collection
     */
    public static function getAllUserResourceWithPermissions(User $user, array $permission, $resource_type, $search, array $search_fields): Collection
    {
        $models = ResourcePermissionRepository::getUserModels($user);
        if (!SearchFieldValidator::resourceTypeExists($resource_type)) {
            throw new \InvalidArgumentException('Invalid resource type: ' . $resource_type);
        }

        $permission_ids = [];

        foreach ($permission as $p) {
            $permission_ids[] = app(ResourcePermissionCache::class)->getPermissionId(AppResourcePermission::fromValue($p));
        }

        $query = ModelHasResourcePermission::where(
            [
                'resource_type' => $resource_type,
            ]
        )
            ->whereIn('resource_permission_id', $permission_ids)
            ->where(function ($query) use ($models) {
                foreach ($models as $model) {
                    $query->orWhere(function ($q) use ($model) {
                        $q->where('model_id', $model['model_id'])
                            ->where('model_type', $model['model_type']);
                    });
                }
            })

            ->when($search, function ($query) use ($search, $resource_type, $search_fields) {
                return $query->join($resource_type, function ($join) use ($resource_type) {
                    $join->on('model_has_resource_permissions.resource_id', '=', $resource_type . '.id');
                })->where(function ($query) use ($search, $resource_type, $search_fields) {
                    foreach ($search_fields as $field) {
                        $query->orWhere("{$resource_type}.{$field}", 'ILIKE', '%' . $search . '%');
                    }
                });
            });

        if ($search) {
            $query = $query->select('resource_id', $resource_type . '.name');
        } else {
            $query = $query->select('resource_id');
        }

        return $query->distinct()->get();
    }

    public static function givePermissionsToEverything(User $user, User $reference)
    {
        $allPermissions = ModelHasResourcePermission::where('model_id', $reference->id)
            ->where('model_type', $reference->getTable())
            ->select(['resource_type', 'resource_id', 'resource_permission_id'])
            ->distinct()
            ->get();

        if ($allPermissions->isEmpty()) {
            return $allPermissions;
        }

        $now = now();
        $newPermissions = $allPermissions->map(function ($permission) use ($user, $now) {
            return [
                'model_id' => $user->id,
                'model_type' => $user->getTable(),
                'resource_permission_id' => $permission->resource_permission_id,
                'resource_type' => $permission->resource_type,
                'resource_id' => $permission->resource_id,
                'created_at' => $now,
                'updated_at' => $now,
            ];
        })->all();

        ModelHasResourcePermission::upsert(
            self::deduplicateRecords($newPermissions),
            ['model_id', 'model_type', 'resource_permission_id', 'resource_type', 'resource_id'],
            ['updated_at']
        );

        return $allPermissions;
    }

    /**
     * Assigns default resource permissions to a user for a given model, 
     * and assigns the model to the user's organization.
     */
    public static function assignDefaultResourcePermissions(User $user, Model $model)
    {
        OrganizationRepository::assignResourceToOrganization($user->organization_id, $model);
        try {
            $default_permissions = AppResourcePermission::defaultPermissions();
            $user->giveResourcePermissionsTo($default_permissions, $model, true);
        } catch (\Exception $e) {
            OrganizationRepository::unassignResourceFromAnyOrganization($model);
            throw $e;
        }
    }

    /**
     * Deletes a model with all its permissions and unassigns it from any organization.
     */
    public static function deleteModelWithResourcePermissions(Model $model)
    {
        ResourcePermissionRepository::deleteAllPermissionsForResource($model);
        OrganizationRepository::unassignResourceFromAnyOrganization($model);
        $model->delete();
    }

    /**
     * Removes duplicate rows from a permission record set before an upsert.
     *
     * PostgreSQL's ON CONFLICT DO UPDATE rejects batches where two or more rows
     * resolve to the same conflict target. This guard ensures uniqueness on the
     * five columns that form the table's unique constraint, keeping the first
     * occurrence of each combination and discarding the rest.
     */
    private static function deduplicateRecords(array $records): array
    {
        $seen = [];

        return array_values(array_filter($records, function (array $record) use (&$seen): bool {
            $key = $record['model_id'] . '|'
                . $record['model_type'] . '|'
                . $record['resource_permission_id'] . '|'
                . $record['resource_type'] . '|'
                . $record['resource_id'];

            if (isset($seen[$key])) {
                return false;
            }

            $seen[$key] = true;
            return true;
        }));
    }
}
