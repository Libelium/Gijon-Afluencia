<?php

namespace App\Repositories;

use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;
use Illuminate\Http\Resources\Json\PaginatedResourceResponse;
use Illuminate\Support\Facades\Auth;

class DashboardRepository
{
    /**
     * Return paginated results using query and filters
     *
     * @return Illuminate\Support\Collection
     */

    private static function applyHiddenFilter($query, $request)
    {
        $value = $request->input('hidden');
        if ($value === 'all') {
            return $query;
        }

        $showHidden = filter_var($value, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
        if ($showHidden === true) {
            return $query->where('dashboards.hidden', true);
        }

        return $query->where('dashboards.hidden', false);
    }

    public static function paginate($request)
    {
        $user_id = Auth::id();

        $query = Dashboard::query()
            ->tap(function ($q) use ($request) {
                self::applyHiddenFilter($q, $request);
            })
            // search
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'ilike', '%' . $search . '%');
            })
            // sort
            ->when($request->sort, function ($query, $sort) use ($request) {
                return $query->orderBy($sort, $request->order === 'asc' ? 'asc' : 'desc');
            })
            // filter
            ->when($request->filter, function ($query, $filter) {
                if ($filter === 'Public') {
                    // Público es el indicador explícito de publicación: tener slug no basta.
                    return $query->where('dashboards.is_published', true);
                } else {
                    // Si no es 'public', asumimos que es un filtro de tipo
                    // (como 'Custom' o 'Template') y aplicamos la condición existente.
                    return $query->where('type', $filter);
                }
            })
            // template_type filter
            ->when($request->template_type, function ($query, $templateTypes) {
                return $query->whereHas('template', function ($q) use ($templateTypes) {
                    $q->whereIn('template_type', $templateTypes);
                });
            })
            // fields
            ->when($request->fields, function ($query, $fields) {
                return $query->select($fields);
            })
            // template
            ->with('template')
            // custom
            ->with('panels')
            // group by
            ->groupBy('dashboards.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            $user_id,
            Dashboard::class
        );

        // pagination
        $dashboards = $query->paginate($request->perPage, ['dashboards.*'], 'page', $request->page);

        foreach ($dashboards->items() as $dashboard) {
            // Generate temporary URL for preview image

            if ($dashboard->type == 'Template') {
                if ($dashboard->template) {
                    $dashboard->template_type = [
                        'type' => $dashboard->template->template_type,
                    ];
                    $dashboard->templateDrawer = $dashboard->template_type;
                }
                $dashboard->entities = [];
            } else if ($dashboard->type == 'Custom') {
                foreach ($dashboard->panels as $panel) {
                    $panel->series = [];
                    $panel->annotations = [];
                }
            }
        }

        return [
            'rows' => $dashboards->items(),
            'count' => $dashboards->total(),
        ];
    }

    /**
     * Return paginated custom dashboards
     *
     * @return array
     */
    public static function getCustomDashboards($request)
    {
        $user_id = Auth::id();

        $query = Dashboard::query()
            ->where('type', 'Custom')
            ->tap(function ($q) use ($request) {
                self::applyHiddenFilter($q, $request);
            })
            // search
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'ilike', '%' . $search . '%');
            })
            // sort
            ->when($request->sort, function ($query, $sort) use ($request) {
                return $query->orderBy($sort, $request->order === 'asc' ? 'asc' : 'desc');
            })
            ->with('panels')
            ->groupBy('dashboards.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            $user_id,
            Dashboard::class
        );

        // pagination
        $dashboards = $query->paginate($request->perPage, ['dashboards.*'], 'page', $request->page);

        foreach ($dashboards->items() as $dashboard) {

            foreach ($dashboard->panels as $panel) {
                $panel->series = [];
                $panel->annotations = [];
            }
        }

        return [
            'rows' => $dashboards->items(),
            'count' => $dashboards->total(),
        ];
    }
}
