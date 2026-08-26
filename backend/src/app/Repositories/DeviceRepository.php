<?php

namespace App\Repositories;

use App\Models\Device;
use App\Models\Entity;
use Illuminate\Database\Eloquent\Collection;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use App\Models\Organization;
use App\Models\Realtime\EntityProperty;
use Illuminate\Support\Facades\DB;

class DeviceRepository
{
    public static function paginate(
        int $userId,
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $searchText = null,
        array|null $realtimeProperties = null
    ) {
        // Si hay searchText, buscar en entity_properties de realtime
        $matchingEntityIds = [];
        if ($searchText) {
            $matchingEntityIds = EntityProperty::select('entity_id')
                ->where('value', 'ILIKE', '%' . $searchText . '%')
                ->orWhere('name', 'ILIKE', '%' . $searchText . '%')
                ->pluck('entity_id')
                ->unique()
                ->toArray();
        }

        $query = Device::with([
            'deviceType',
            'entities' => function ($query) {
                $query->select('entities.id');
            },
        ])
            ->orderBy($orderColumn, $orderDirection)
            ->groupBy('devices.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            $userId,
            Device::class
        );

        if ($searchText) {
            $query = self::searchTextQuery($query, $searchText, $matchingEntityIds);
        }

        $paginated = $query->paginate($paginationSize, ['devices.*'], 'page', $page);

        if ($realtimeProperties) {
            $entityIds = $paginated->getCollection()
                ->flatMap(function ($device) {
                    return $device->entities;
                })
                ->pluck('id')
                ->unique()
                ->toArray();

            if (!empty($entityIds)) {
                $entitiesWithProps = Entity::whereIn('id', $entityIds)
                    ->with(['entityProperties' => function ($query) use ($realtimeProperties) {
                        $query->whereIn('name', $realtimeProperties);
                    }])
                    ->get()
                    ->keyBy('id');

                // Inyectar propiedades filtradas a los dispositivos ya paginados
                foreach ($paginated->getCollection() as $device) {
                    foreach ($device->entities as $entity) {
                        if ($entitiesWithProps->has($entity->id)) {
                            $entity->setRelation(
                                'entityProperties',
                                $entitiesWithProps[$entity->id]->entityProperties
                            );
                        }
                    }
                }
            }
        }
        $paginatedDeviceIds = $paginated->getCollection()->pluck('id')->toArray();

        if (!empty($paginatedDeviceIds)) {

            $allEntityIdsForPage = DB::table('device_entity')
                ->whereIn('device_id', $paginatedDeviceIds)
                ->pluck('entity_id')
                ->unique();

            $entityTimestamps = EntityProperty::query()
                ->whereIn('entity_id', $allEntityIdsForPage)
                ->groupBy('entity_id')
                ->select('entity_id', DB::raw('MAX(timestamp) as max_ts'))
                ->pluck('max_ts', 'entity_id'); // Creates a map [entity_id => timestamp]

            foreach ($paginated->getCollection() as $device) {
                $latestTimestampForDevice = null;

                foreach ($device->entities as $entity) {
                    $timestamp = $entityTimestamps->get($entity->id);

                    // Check if this entity's timestamp is the latest one
                    if ($timestamp && (is_null($latestTimestampForDevice) || $timestamp > $latestTimestampForDevice)) {
                        $latestTimestampForDevice = $timestamp;
                    }
                }

                $device->setAttribute('time_last_data', $latestTimestampForDevice);
            }
        }
        return $paginated;
    }

    public static function paginateExclusivePhysicalDevicesTimestamp(
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $searchText = null,
        array|null $realtimeProperties = null,
        int|null $organizationId = null
    ) {
        // Si hay searchText, buscar en entity_properties de realtime
        $matchingEntityIds = [];
        if ($searchText) {
            $matchingEntityIds = EntityProperty::select('entity_id')
                ->where('value', 'ILIKE', '%' . $searchText . '%')
                ->orWhere('name', 'ILIKE', '%' . $searchText . '%')
                ->pluck('entity_id')
                ->unique()
                ->toArray();
        }

        $query = Device::with([
            'deviceType',
            'entities' => function ($query) {
                $query->select('entities.id');
            },
        ])
            ->orderBy($orderColumn, $orderDirection)
            ->groupBy('devices.id');

        if ($organizationId) {
            $organization = Organization::findOrFail($organizationId);
            $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
                $query,
                AppResourcePermission::READ,
                $organization->admin,
                Device::class
            );
        }

        if ($searchText) {
            $query = self::searchTextQuery($query, $searchText, $matchingEntityIds);
        }

        $paginated = $query->paginate($paginationSize, ['devices.*'], 'page', $page);

        if ($realtimeProperties) {
            $entityIds = $paginated->getCollection()
                ->flatMap(function ($device) {
                    return $device->entities;
                })
                ->pluck('id')
                ->unique()
                ->toArray();

            if (!empty($entityIds)) {
                $entitiesWithProps = Entity::whereIn('id', $entityIds)
                    ->with(['entityProperties' => function ($query) use ($realtimeProperties) {
                        $query->whereIn('name', $realtimeProperties);
                    }])
                    ->get()
                    ->keyBy('id');

                foreach ($paginated->getCollection() as $device) {
                    foreach ($device->entities as $entity) {
                        if ($entitiesWithProps->has($entity->id)) {
                            $entity->setRelation(
                                'entityProperties',
                                $entitiesWithProps[$entity->id]->entityProperties
                            );
                        }
                    }
                }
            }
        }

        $paginatedDeviceIds = $paginated->getCollection()->pluck('id')->toArray();

        if (!empty($paginatedDeviceIds)) {

            $allEntityIdsForPage = DB::table('device_entity')
                ->join('entities', 'device_entity.entity_id', '=', 'entities.id')
                ->whereIn('device_entity.device_id', $paginatedDeviceIds)
                ->where('entities.tenant', 'NOT LIKE', '%\_platform')
                ->pluck('device_entity.entity_id')
                ->unique();

            $entityTimestamps = EntityProperty::query()
                ->whereIn('entity_id', $allEntityIdsForPage)
                ->whereNotIn('name', ['name', 'location', 'commands'])
                ->groupBy('entity_id')
                ->select('entity_id', DB::raw('MAX(timestamp) as max_ts'))
                ->pluck('max_ts', 'entity_id');

            foreach ($paginated->getCollection() as $device) {
                $latestTimestampForDevice = null;

                foreach ($device->entities as $entity) {
                    $timestamp = $entityTimestamps->get($entity->id);

                    if ($timestamp && (is_null($latestTimestampForDevice) || $timestamp > $latestTimestampForDevice)) {
                        $latestTimestampForDevice = $timestamp;
                    }
                }

                $device->setAttribute('time_last_data', $latestTimestampForDevice);
            }

            $deviceOrganizationsQuery = DB::table('organization_has_resource')
                ->join('organizations', 'organization_has_resource.organization_id', '=', 'organizations.id')
                ->whereIn('organization_has_resource.resource_id', $paginatedDeviceIds)
                ->where('organization_has_resource.resource_type', 'devices')
                ->select(
                    'organization_has_resource.resource_id as device_id',
                    'organizations.id',
                    'organizations.name'
                );

            if ($organizationId) {
                $deviceOrganizationsQuery->where('organization_has_resource.organization_id', $organizationId);
            }

            $deviceOrganizations = $deviceOrganizationsQuery->get()->keyBy('device_id');

            foreach ($paginated->getCollection() as $device) {
                $org = $deviceOrganizations->get($device->id);
                $device->setAttribute('organization', $org
                    ? ['id' => $org->id, 'name' => $org->name]
                    : null
                );
            }
        }

        return $paginated;
    }


    public static function paginateAll(
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $searchText = null,
        array|null $types = null,
        int|null $organizationId = null
    ) {
        $query = Device::with([
            'deviceType',
            'entities',
        ])
            ->orderBy($orderColumn, $orderDirection)
            ->groupBy('devices.id');

        if ($types) {
            $query->whereIn('device_type_id', $types);
        }

        if ($organizationId) {
            $organization = Organization::findOrFail($organizationId);

            $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
                $query,
                AppResourcePermission::READ,
                $organization->admin,
                Device::class
            );
        }

        if ($searchText) {
            $query = self::searchTextQuery($query, $searchText);
        }

        return $query->paginate($paginationSize, ['devices.*'], 'page', $page);
    }

    public static function paginateFull(
        int $userId,
        int $paginationSize,
        int $page,
        string $orderColumn,
        string $orderDirection,
        string|null $searchText = null
    ) {
        $query = Device::with([
            'deviceType',
            'entities',
            'entities.fiwareScope.tenant',
            'entities.entityProperties'
        ])
            ->orderBy($orderColumn, $orderDirection)
            ->groupBy('devices.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            $userId,
            Device::class
        );

        if ($searchText) {
            $query = self::searchTextQuery($query, $searchText);
        }

        return $query->paginate($paginationSize, ['devices.*'], 'page', $page);
    }


    private static function searchTextQuery(object $query, string $searchText, array|null $matchingEntityIds = null): object
    {
        return $query->where(function ($query2) use ($searchText, $matchingEntityIds) {
            $query2->where('devices.name', 'ILIKE', '%' . $searchText . '%')
                ->orWhere('devices.serial', 'ILIKE', '%' . $searchText . '%')
                ->orWhere('devices.case_id', 'ILIKE', '%' . $searchText . '%')
                ->orWhereHas('deviceType', function ($query3) use ($searchText) {
                    $query3->where('name', 'ILIKE', '%' . $searchText . '%');
                });

            if (!empty($matchingEntityIds)) {
                $query2->orWhereHas('entities', function ($query4) use ($matchingEntityIds) {
                    $query4->whereIn('entities.id', $matchingEntityIds);
                });
            }
        });
    }



}
