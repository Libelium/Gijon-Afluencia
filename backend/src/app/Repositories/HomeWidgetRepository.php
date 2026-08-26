<?php

namespace App\Repositories;

use App\Models\HomeWidget;

class HomeWidgetRepository
{
    public static function paginate($request, int $layoutId)
    {
        $query = HomeWidget::query()
            ->where('home_layout_id', $layoutId);

        $widgets = $query->paginate($request->perPage);

        return [
            'rows' => $widgets->items(),
            'count' => $widgets->total(),
        ];
    }
}
