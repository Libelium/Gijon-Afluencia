<?php

namespace App\Repositories;

use App\Models\OutConnectors\OutConnector;
use App\Authorization\AppResourcePermission;
use App\Services\OrderFieldValidator;

class OutConnectorRepository
{
    /** Columns an out connector listing may be ordered by — the ones queryShared() selects. */
    private const ORDERABLE_COLUMNS = [
        'id',
        'name',
        'type',
        'status',
        'user_id',
        'last_connection',
        'created_at',
        'updated_at',
    ];

    private const DEFAULT_ORDER_COLUMN = 'out_connectors.id';

    /**
     * Return paginated results using query and filters
     */
    public static function paginate($userId, $pagination_size, $page, $order_column, $order_direction, $search_text = null): array
    {
        $order_column = OrderFieldValidator::resolveColumn(
            $order_column,
            self::ORDERABLE_COLUMNS,
            self::DEFAULT_ORDER_COLUMN,
            'out_connectors'
        );
        $order_direction = OrderFieldValidator::resolveDirection($order_direction);

        $out_connectors = self::queryShared($userId, $search_text)
            ->orderBy($order_column, $order_direction)
            ->paginate($pagination_size, ['*'], 'page', $page);

        return [
            'rows' => $out_connectors->items(),
            'count' => $out_connectors->total(),
        ];
    }

    private static function setSearch($query, $search_text)
    {
        return $query
            ->when($search_text, function ($query, $search_text) {
                $query->where(function ($query) use ($search_text) {
                    $query->where('out_connectors.name', 'ILIKE', '%' . $search_text . '%')
                        ->orWhere('out_connectors.type', 'ILIKE', '%' . $search_text . '%');
                });
            });
    }

    private static function queryShared($userId, $search_text = null)
    {
        $query = OutConnector::select(
            'out_connectors.id',
            'out_connectors.name',
            'out_connectors.type',
            'out_connectors.status',
            'out_connectors.user_id',
            'out_connectors.last_connection',
            'out_connectors.created_at',
            'out_connectors.updated_at',
        );

        $search_query = self::setSearch($query, $search_text);

        return ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $search_query,
            AppResourcePermission::READ,
            $userId,
            OutConnector::class
        );
    }
}
