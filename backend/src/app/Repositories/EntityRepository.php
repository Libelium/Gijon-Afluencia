<?php

namespace App\Repositories;

use App\Models\Entity;
use App\Models\User;
use Illuminate\Database\Eloquent\Collection;
use App\Authorization\AppResourcePermission;
use App\Authorization\ResourcePermissionCache;
use App\Models\EntityHealthcheck;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Realtime\EntityProperty;
use App\Services\OrderFieldValidator;
use Illuminate\Support\Facades\App;
use Illuminate\Support\Facades\DB;
class EntityRepository
{

    private static $hiddenUrns = [
        'urn:ngsi-ld:AirQualityObserved:Simulation_%',
        'urn:ngsi-ld:PointOfInterest:Simulation_%',
        'urn:ngsi-ld:PlatformAlarm:%',
        'urn:ngsi-ld:CrowdFlowEventETL:%:%',
    ];

    /** Columns an entity listing may be ordered by. See OrderFieldValidator for the why. */
    private const ORDERABLE_ENTITY_COLUMNS = [
        'id',
        'urn',
        'datamodel',
        'tenant',
        'scope',
        'fiware_scope_id',
        'created_at',
        'updated_at',
    ];

    /** Default order for entity listings when the requested column is not allowed. */
    private const DEFAULT_ENTITY_ORDER_COLUMN = 'entities.id';

    /**
     * Aliases a healthcheck listing may be ordered by. They are the aggregates built in the
     * SELECT of paginateHealthchecks, plus the grouping key.
     */
    private const ORDERABLE_HEALTHCHECK_COLUMNS = [
        'urn',
        'device_id',
        'serial',
        'device_type',
        'firmware_version',
        'overall_status',
        'reason',
        'battery_status',
        'signal_status',
        'send_frequency_status',
        'battery_reason',
        'signal_reason',
        'send_frequency_reason',
    ];

    /** Default order for healthcheck listings when the requested column is not allowed. */
    private const DEFAULT_HEALTHCHECK_ORDER_COLUMN = 'overall_status';


    public static function getEntitiesQuery(
        int $userId,
        string $orderColumn,
        string $orderDirection,
        string|null $tenant = null,
        string|null $scope = null,
        string|null $searchText = null,
        array|null $types = null,
        array|null $groups = null,
        bool $onlyCanUpdate = false,
        array|null $excluded = null,
        array|null $bounds = null,
        array|null $urn = null,
    ) {
        $orderColumn = OrderFieldValidator::resolveColumn(
            $orderColumn,
            self::ORDERABLE_ENTITY_COLUMNS,
            self::DEFAULT_ENTITY_ORDER_COLUMN,
            'entities'
        );
        $orderDirection = OrderFieldValidator::resolveDirection($orderDirection);

        $query = Entity::distinct()->with(
            [
                'devices' => function ($query) {
                    $query->select('devices.id');
                },
                'geolocation',
                'fiwareScope',
                'name',
                'fiwareScope.tenant'
            ]
        )
            ->orderBy($orderColumn, $orderDirection)
            // Se agrega el groupBy para evitar duplicados
            ->groupBy('entities.id');

        foreach (self::$hiddenUrns as $hiddenUrn) {
            $query->where('entities.urn', 'not like', $hiddenUrn);
        }

        if ($excluded) {
            foreach ($excluded as $er) {
                $query->where('entities.urn', 'not like', $er);
            }
        }

        if ($urn) {
            $query->where(function ($q) use ($urn) {
                foreach ($urn as $pattern) {
                    $q->orWhere('entities.urn', 'like', $pattern);
                }
            });
        }

        if ($tenant) {
            $query->where('entities.tenant', $tenant);
        }

        if ($scope) {
            $query->where('entities.scope', $scope);
        }

        if ($types) {
            $query->whereIn('entities.datamodel', $types);
        }

        if ($groups) {
            $query->join('entity_entity_group', function ($join) use ($groups) {
                $join->on('entities.id', '=', 'entity_entity_group.entity_id')
                    ->whereIn('entity_entity_group.entity_group_id', $groups);
            });
        }

        if ($searchText) {
            $query = self::searchTextQuery($query, $searchText);
        }

        if ($bounds) {
            $query->whereIn('entities.urn', self::urnsWithinBounds($bounds, $tenant, $scope));
        }

        return self::updateRequestWithPermissionCheck($query, $userId, $onlyCanUpdate ? AppResourcePermission::UPDATE : AppResourcePermission::READ);
    }

    private static function urnsWithinBounds(array $bounds, ?string $tenant, ?string $scope)
    {
        $pointGuard = "value ~ '[''\"]Point[''\"]'";
        $longitude = "(CASE WHEN $pointGuard THEN substring(value from 'coordinates[^\[]{0,4}\[\s*(-?[0-9]+\.?[0-9]*)') END)::float8";
        $latitude = "(CASE WHEN $pointGuard THEN substring(value from 'coordinates[^\[]{0,4}\[\s*-?[0-9]+\.?[0-9]*\s*,\s*(-?[0-9]+\.?[0-9]*)') END)::float8";

        return DB::connection('pgsql_realtime')
            ->table('entity_properties')
            ->where('name', 'location')
            ->when($tenant, fn ($q) => $q->where('tenant', $tenant))
            ->when($scope, fn ($q) => $q->where('scope', $scope))
            ->whereRaw("$latitude BETWEEN ? AND ?", [(float) $bounds['south'], (float) $bounds['north']])
            ->whereRaw("$longitude BETWEEN ? AND ?", [(float) $bounds['west'], (float) $bounds['east']])
            ->distinct()
            ->pluck('urn');
    }
    public static function paginate(
        int $userId,
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $tenant = null,
        string|null $scope = null,
        string|null $searchText = null,
        array|null $types = null,
        array|null $groups = null,
        bool $onlyCanUpdate = false,
        array|null $excluded = null,
        array|null $bounds = null,
        array|null $urn = null,
    ) {

        $query = self::getEntitiesQuery($userId, $orderColumn, $orderDirection, $tenant, $scope, $searchText, $types, $groups, $onlyCanUpdate, $excluded, $bounds, $urn);

        return $query->paginate($paginationSize, ['entities.*'], 'page', $page);
    }

    public static function list(
        int $userId,
        string $orderColumn,
        string $orderDirection,
        string|null $tenant = null,
        string|null $scope = null,
        string|null $searchText = null,
        array|null $types = null,
        array|null $groups = null,
        bool $onlyCanUpdate = false,
        array|null $excluded = null,
    ) {

        $query = self::getEntitiesQuery($userId, $orderColumn, $orderDirection, $tenant, $scope, $searchText, $types, $groups, $onlyCanUpdate, $excluded);

        return $query->get(['entities.*']);
    }

    public static function getDatamodelsQuery(
        int $userId,
        string|null $tenant = null,
        string|null $scope = null,
        string|null $searchText = null,
    ) {
        $query = Entity::query()
            ->select('entities.datamodel')
            ->whereNotNull('entities.datamodel')
            ->groupBy('entities.datamodel')
            ->orderBy('entities.datamodel', 'asc');

        foreach (self::$hiddenUrns as $hiddenUrn) {
            $query->where('entities.urn', 'not like', $hiddenUrn);
        }

        if ($tenant) {
            $query->where('entities.tenant', $tenant);
        }

        if ($scope) {
            $query->where('entities.scope', $scope);
        }

        if ($searchText) {
            $query->where('entities.datamodel', 'ILIKE', '%' . $searchText . '%');
        }

        return self::updateRequestWithPermissionCheck($query, $userId, AppResourcePermission::READ);
    }

    // Returns every distinct datamodel the user can access in one query. The set
    // is small, so we avoid ->paginate() (which adds a heavy COUNT over the
    // grouped, permission-joined subquery) and let the client search/paginate.
    public static function listDatamodels(
        int $userId,
        string|null $tenant = null,
        string|null $scope = null,
        string|null $searchText = null,
    ) {
        $query = self::getDatamodelsQuery($userId, $tenant, $scope, $searchText);

        return $query->get(['entities.datamodel']);
    }

    public static function getWithPermissions($user_id, $permissions, $searchText = null, $searchFields = ['datamodel', 'urn']): Collection
    {
        $query = Entity::distinct()->with(
            [
                'fiwareScope',
                'fiwareScope.tenant',
                'name'
            ]
        );

        foreach (self::$hiddenUrns as $hiddenUrn) {
            $query->where('entities.urn', 'not like', $hiddenUrn);
        }

        if ($searchText) {
            // Step 1: Query `entity_properties` for matching `entity_id`s
            $matchingEntityIds = EntityProperty::where('name', 'name')
                ->where('value', 'ILIKE', '%' . $searchText . '%')
                ->pluck('entity_id');

            // Step 2: Use these IDs in the main `Entity` query
            $query->where(function ($query2) use ($searchText, $searchFields, $matchingEntityIds) {
                foreach ($searchFields as $field) {
                    if ($field === 'name') {
                        $query2->orWhereIn('entities.id', $matchingEntityIds);
                    } else {
                        $query2->orWhere("entities.{$field}", 'ILIKE', '%' . $searchText . '%');
                    }
                }
            });
        }

        $appPermissions = [];

        foreach ($permissions as $permission) {
            $appPermissions[] = AppResourcePermission::fromValue($permission);
        }

        $query = self::updateRequestWithPermissionsCheck($query, $user_id, $appPermissions);

        return $query->select('entities.id', 'entities.urn', 'entities.datamodel')->get();
    }

    public static function updateRequestWithPermissionCheck(
        object $query,
        int $userId,
        AppResourcePermission $permission
    ): object {

        $with_scopes = $query->join(
            'fiware_scopes',
            'entities.fiware_scope_id',
            '=',
            'fiware_scopes.id'
        );

        $permission_id = app(ResourcePermissionCache::class)->getPermissionId($permission);

        $models = ResourcePermissionRepository::getUserModels(User::find($userId));

        $with_permission = $with_scopes->join(
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
                                    ->on('model_has_resource_permissions.resource_id', 'entities.fiware_scope_id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareScope())->getTable());
                            }
                        );

                        $join->orOn(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'entities.id')
                                    ->where('model_has_resource_permissions.resource_type', (new Entity())->getTable());
                            }
                        );
                    }
                );
            }
        );

        return $with_permission;
    }

    private static function updateRequestWithPermissionsCheck(
        object $query,
        int $userId,
        array $permissions
    ): object {

        $with_scopes = $query->join(
            'fiware_scopes',
            'entities.fiware_scope_id',
            '=',
            'fiware_scopes.id'
        );

        $permission_ids = [];

        foreach ($permissions as $permission) {
            $permission_ids[] = app(ResourcePermissionCache::class)->getPermissionId($permission);
        }

        $models = ResourcePermissionRepository::getUserModels(User::find($userId));

        $with_permission = $with_scopes->join(
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
                                    ->on('model_has_resource_permissions.resource_id', 'entities.fiware_scope_id')
                                    ->where('model_has_resource_permissions.resource_type', (new FiwareScope())->getTable());
                            }
                        );

                        $join->orOn(
                            function ($query) {
                                $query
                                    ->on('model_has_resource_permissions.resource_id', 'entities.id')
                                    ->where('model_has_resource_permissions.resource_type', (new Entity())->getTable());
                            }
                        );
                    }
                );
            }
        );

        return $with_permission;
    }

    private static function searchTextQuery(object $query, string $searchText): object
    {
        $matchingEntityIds = EntityProperty::where('name', 'name')
            ->whereRaw("LOWER(value) LIKE ?", ["%" . strtolower($searchText) . "%"])
            ->pluck('entity_id');

        return $query->where(function ($query2) use ($searchText, $matchingEntityIds) {
            $query2->where('entities.urn', 'ILIKE', '%' . $searchText . '%')
                ->orWhere('entities.datamodel', 'ILIKE', '%' . $searchText . '%')
                ->orWhereIn('entities.id', $matchingEntityIds);
        });
    }

    public static function paginateHealthchecks(
        int $userId,
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $searchText = null,
        array $selectedDeviceTypes = [],
        array $selectedStatus = [],
        array $selectedOrganizations = []
    ) {
        $orderColumn = OrderFieldValidator::resolveColumn(
            $orderColumn,
            self::ORDERABLE_HEALTHCHECK_COLUMNS,
            self::DEFAULT_HEALTHCHECK_ORDER_COLUMN
        );
        $orderDirection = OrderFieldValidator::resolveDirection($orderDirection);

        // Define the healthcheck properties and their types for casting
        $healthcheckProperties = [
            'device_id' => 'string',
            'serial' => 'string',
            'device_type' => 'string',
            'firmware_version' => 'string',
            'overall_status' => 'numeric',
            'reason' => 'string',
            'battery_status' => 'numeric',
            'signal_status' => 'numeric',
            'send_frequency_status' => 'numeric',
            'battery_reason' => 'string',
            'signal_reason' => 'string',
            'send_frequency_reason' => 'string',
        ];

        // Build the SELECT statements with conditional aggregation
        $selects = ['urn'];

        $baseProperties = [
            'device_id',
            'serial',
            'device_type',
            'firmware_version',
            'reason',
            'battery_reason',
            'signal_reason',
            'send_frequency_reason',
        ];

        foreach ($baseProperties as $prop) {
            $selects[] = DB::raw("MAX(CASE WHEN name = '$prop' THEN value END) AS $prop");
        }

        $numericProperties = [
            'overall_status',
            'battery_status',
            'signal_status',
            'send_frequency_status'
        ];

        foreach ($numericProperties as $prop) {
            $selects[] = DB::raw("CAST(MAX(CASE WHEN name = '$prop' THEN value END) AS NUMERIC) AS $prop");
        }
        $filteredDeviceIds = [];
        if (!empty($selectedOrganizations)) {
            $filteredDeviceIds = DB::table('organization_has_resource')
                ->where('resource_type', 'devices')
                ->whereIn('organization_id', $selectedOrganizations)
                ->pluck('resource_id')
                ->toArray();

            if (empty($filteredDeviceIds)) {
                return new \Illuminate\Pagination\LengthAwarePaginator([], 0, $paginationSize, $page);
            }
        }

        $query = EntityHealthcheck::select($selects)
            ->where('urn', 'ILIKE', '%DeviceHealthcheck%')
            ->whereIn('name', array_keys($healthcheckProperties))
            ->groupBy('urn')
            ->orderBy($orderColumn, $orderDirection);

        if ($searchText) {
            $query = self::searchTextQueryHealthchecks($query, $searchText);
        }

        if (!empty($selectedDeviceTypes)) {
            $placeholders = implode(',', array_fill(0, count($selectedDeviceTypes), '?'));

            $query->havingRaw(
                "MAX(CASE WHEN name = 'device_type' THEN value END) IN ({$placeholders})",
                $selectedDeviceTypes
            );
        }

        if (!empty($selectedStatus)) {
            $placeholders = implode(',', array_fill(0, count($selectedStatus), '?'));

            $query->havingRaw(
                "MAX(CASE WHEN name = 'overall_status' THEN value END) IN ({$placeholders})",
                $selectedStatus
            );
        }


        if (!empty($filteredDeviceIds)) {
            $placeholders = implode(',', array_fill(0, count($filteredDeviceIds), '?'));

            $query->havingRaw(
                "MAX(CASE WHEN name = 'device_id' THEN value END) IN ({$placeholders})",
                $filteredDeviceIds
            );
        }

        $paginator = $query->paginate($paginationSize, ['*'], 'page', $page);

        if ($paginator->isEmpty()) {
            return $paginator;
        }
        $deviceIds = $paginator->getCollection()->pluck('device_id')->toArray();

        $organizationData = DB::table('organization_has_resource', 't2')
            ->select('t3.name AS organization_name', 't2.resource_id')
            ->join('organizations AS t3', 't3.id', '=', 't2.organization_id')
            ->where('t2.resource_type', 'devices')
            ->whereIn('t2.resource_id', $deviceIds)
            ->get()
            ->keyBy('resource_id')
            ->map(fn($item) => $item->organization_name)
            ->toArray();

        $updatedCollection = $paginator->getCollection()->map(function ($healthcheck) use ($organizationData) {
            $organizationName = $organizationData[$healthcheck->device_id] ?? null;

            $healthcheck->organization_name = $organizationName;

            return $healthcheck;
        });

        return $paginator->setCollection($updatedCollection);
    }

    private static function searchTextQueryHealthchecks(object $query, string $searchText): object
    {
        $stringProperties = [
            'serial',
            'device_type',
            'firmware_version',
        ];

        $havingClauses = [];
        $bindings = [];

        foreach ($stringProperties as $prop) {
            $havingClauses[] = "MAX(CASE WHEN name = ? THEN value END) ILIKE ?";
            $bindings[] = $prop;
            $bindings[] = '%' . $searchText . '%';
        }

        $rawHaving = '(' . implode(' OR ', $havingClauses) . ')';

        return $query->havingRaw($rawHaving, $bindings);
    }
}
