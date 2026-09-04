<?php

namespace App\Repositories;

use App\Http\V1\Requests\Log\LogsTableDataRequest;

use App\Models\Device;
use App\Models\Entity;
use App\Models\EntityGroup;
use App\Models\Organization;
use App\Models\FiwareTenant;
use App\Models\Regulation;
use App\Models\FiwareScope;
use App\Models\Dashboard;
use App\Models\OutConnectors\OutConnector;
use App\Models\Log\Line;
use App\Models\User;
use App\Models\Alarm;
use App\Models\BackgroundJob;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use Illuminate\Support\Facades\DB;

class LogsRepository
{
    private static array $tablesToModel = [
        'devices' => Device::class,
        'out_connectors' => OutConnector::class,
        'entities' => Entity::class,
        'entity_groups' => EntityGroup::class,
        'organizations' => Organization::class,
        'users' => User::class,
        'dashboards' => Dashboard::class,
        'fiware_tenants' => FiwareTenant::class,
        'regulations' => Regulation::class,
        'fiware_scopes' => FiwareScope::class,
        'alarms' => Alarm::class,
        'background_jobs' => BackgroundJob::class,
    ];


    public static function paginate(int $userId, LogsTableDataRequest $request)
    {
        $query = Line::when($request->search, function ($query, $search) {
            return $query->where('log_lines.message', 'like', '%' . $search . '%');
        })
            ->when($request->orderBy, function ($query, $orderBy) use ($request) {
                return $query->orderBy($orderBy, $request->orderDirection ? 'asc' : 'desc');
            })
            ->when($request->start_date, function ($query, $start_date) {
                return $query->where('log_lines.datetime', '>=', $start_date);
            })
            ->when($request->end_date, function ($query, $end_date) {
                return $query->where('log_lines.datetime', '<=', $end_date);
            })
            ->when($request->level, function ($query, $level) {
                if ($level == 'WARNING') {
                    return $query->whereNotIn('log_lines.level_name', ['INFO']);
                } else if ($level == 'ERROR') {
                    return $query->where('log_lines.level_name', 'like', '%' . $level . '%');
                }
            })
            ->when($request->resource_type, function ($query, $resource_type) {
                return $query->where('log_lines.resource_type', $resource_type);
            })
            ->when($request->resource_id, function ($query, $resource_id) {
                return $query->whereIn('log_lines.resource_id', $resource_id);
            });

        $query = $query->groupBy('log_lines.id');

        // update query with permission check
        if ($request->resource_type == 'entities') {
            $resources = EntityRepository::getWithPermissions($userId, ['read']);

            $resource_ids = $resources->pluck('id')->toArray();

            $query->where(function ($query) use ($resource_ids) {
                $query->whereIn('log_lines.resource_id', $resource_ids);
            });
        } elseif ($request->resource_type == 'data_importation') {
            // For data_importation logs, filter by user_id (resource_id contains the user who initiated the import)
            $query->where('log_lines.resource_id', $userId);
        } else {
            $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
                $query,
                AppResourcePermission::READ,
                $userId,
                Line::class,
                true
            );
        }

        $logs = $query->paginate(
            $request->paginationSize,
            ['log_lines.*'],
            'page',
            $request->page
        );

        $logs->each(function ($log) {
            if ($log->resource_type === 'data_importation') {
                $user = User::find($log->resource_id);
                $log->resource_name = $user ? $user->name : 'Unknown User';
            } else {
                $model = self::$tablesToModel[$log->resource_type] ?? null;
                if ($model) {
                    $resource = $model::find($log->resource_id);
                    $log->resource_name = $resource ? $resource->name : 'Unknown';
                } else {
                    $log->resource_name = 'Unknown';
                }
            }
        });

        return [
            'rows' => $logs->items(),
            'count' => $logs->total(),
        ];
    }

    public static function create(String $message, String $level, String $resourceType, int $resourceId, array $extra = [])
    {
        if (!in_array($level, ['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY'])) {
            throw new \Exception('Invalid log level');
        }

        if (!array_key_exists($resourceType, self::$tablesToModel)) {
            throw new \Exception('Invalid resource type');
        }

        $data = [
            'message' => $message,
            'level_name' => $level,
            'extra' => $extra,
            'datetime' => now(),
            'resource_type' => $resourceType,
            'resource_id' => $resourceId,
        ];

        $line = Line::create($data);

        return $line;
    }

    public static function createConnectorLog(int $resourceId, array $oldValues = [], array $newValues = [])
    {
        $changes = [];

        foreach ($newValues as $key => $newValue) {
            $oldValue = $oldValues[$key] ?? null;

            if ($oldValue !== $newValue) {
                $changes[$key] = [
                    'old' => $oldValue,
                    'new' => $newValue,
                ];
            }
        }

        $extra = [
            'changes' => $changes,
        ];

        self::create(
            'Connector has been updated',
            'INFO',
            'out_connectors',
            $resourceId,
            $extra
        );
    }
}
