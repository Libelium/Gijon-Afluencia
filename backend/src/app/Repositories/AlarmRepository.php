<?php

namespace App\Repositories;

use App\Models\Alarm;
use Illuminate\Support\Facades\Auth;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use App\Services\OrderFieldValidator;

class AlarmRepository
{
    /** Columns an alarm listing may be ordered by — the ones queryShared() selects. */
    private const ORDERABLE_COLUMNS = [
        'id',
        'user_id',
        'name',
        'type',
        'function',
        'up',
        'disabled',
        'created_at',
        'updated_at',
    ];

    private const DEFAULT_ORDER_COLUMN = 'alarms.id';

    /**
     * Return paginated results using query and filters
     *
     * @return Illuminate\Support\Collection
     */
    public static function paginate($userId, $pagination_size, $page, $order_column, $order_direction, $search_text = null): array
    {
        $order_column = OrderFieldValidator::resolveColumn(
            $order_column,
            self::ORDERABLE_COLUMNS,
            self::DEFAULT_ORDER_COLUMN,
            'alarms'
        );
        $order_direction = OrderFieldValidator::resolveDirection($order_direction);

        $alarms = self::queryShared($userId, $search_text)
            ->orderBy($order_column, $order_direction)
            ->paginate($pagination_size, ['*'], 'page', $page);

        return [
            'rows' => $alarms->items(),
            'count' => $alarms->total(),
        ];
    }

    /**
     * Makes the main part of the query, with filters and conditions to restrict the search
     * @param $query
     * @param $search_text
     * @param $filters
     * @return object
     */
    private static function setSearch($query, $search_text)
    {
        return $query
            ->when($search_text, function ($query, $search_text) {
                $query->where('alarms.name', 'ILIKE', '%' . $search_text . '%');
            });
    }

    private static function queryShared($userId, $search_text = null)
    {
        $query = Alarm::select(
            'alarms.id',
            'alarms.user_id',
            'alarms.name',
            'alarms.type',
            'alarms.function',
            'alarms.up',
            'alarms.disabled',
            'alarms.created_at',
            'alarms.updated_at',
        );

        $search_query = self::setSearch($query, $search_text);

        return ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $search_query,
            AppResourcePermission::READ,
            $userId,
            Alarm::class
        );
    }
}
