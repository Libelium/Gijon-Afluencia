<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Resources\HomeWidgetResource;
use App\Models\HomeLayout;
use App\Models\HomeWidget;
use App\Repositories\HomeWidgetRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class HomeWidgetController extends Controller
{
    public function paginate(Request $request, int $layoutId)
    {
        $request->validate([
            'page' => 'numeric',
            'perPage' => 'numeric',
        ]);

        $layout = HomeLayout::findOrFail($layoutId);

        $this->authorize('read', $layout);

        $widgets = HomeWidgetRepository::paginate($request, $layoutId);

        $result = [
            'count' => $widgets['count'],
            'rows' => $widgets['rows'],
            'items' => $widgets['rows'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }


    public function store(Request $request, int $layoutId)
    {
        $request->validate([
            'type' => 'required|string|max:32',
            'config' => 'array|nullable',
        ]);

        $layout = HomeLayout::findOrFail($layoutId);

        $this->authorize('update', $layout);

        $widget = HomeWidget::create([
            'user_id' => Auth::id(),
            'home_layout_id' => $layoutId,
            'type' => $request->type,
            'config' => $request->config,
        ]);

        return new HomeWidgetResource($widget);
    }

    // Only config can be updated on a widget
    public function update(Request $request, int $id)
    {
        $request->validate([
            'config' => 'array|nullable',
        ]);

        $widget = HomeWidget::findOrFail($id);
        $layout = HomeLayout::findOrFail($widget->home_layout_id);

        $this->authorize('update', $layout);

        $widget->update([
            'config' => $request->config,
        ]);

        return new HomeWidgetResource($widget);
    }

    public function destroy(int $id)
    {
        $widget = HomeWidget::findOrFail($id);
        $layout = HomeLayout::findOrFail($widget->home_layout_id);

        $this->authorize('update', $layout);

        $widget->delete();

        return response()->json(true, 200);
    }


    public function batchStore(Request $request, int $layoutId)
    {
        $request->validate([
            'widgets' => 'required|array',
            'widgets.*.type' => 'required|string|max:32',
            'widgets.*.config' => 'array|nullable',
        ]);

        $layout = HomeLayout::findOrFail($layoutId);

        $this->authorize('update', $layout);

        $createdWidgets = [];

        foreach ($request->widgets as $widgetData) {
            $widget = HomeWidget::create([
                'user_id' => Auth::id(),
                'home_layout_id' => $layoutId,
                'type' => $widgetData['type'],
                'config' => $widgetData['config'] ?? null,
            ]);

            $createdWidgets[] = new HomeWidgetResource($widget);
        }
        return response()->json([
            'widgets' => $createdWidgets,
        ], 200);
    }

    public function batchUpdate(Request $request, int $layoutId)
    {
        $request->validate([
            'widgets' => 'required|array',
            'widgets.*.id' => 'required|integer|exists:home_widgets,id',
            'widgets.*.config' => 'array|nullable',
        ]);

        $layout = HomeLayout::findOrFail($layoutId);

        $this->authorize('update', $layout);

        $updatedWidgets = [];

        foreach ($request->widgets as $widgetData) {
            $widget = HomeWidget::findOrFail($widgetData['id']);

            // Verify widget belongs to this layout
            if ($widget->home_layout_id !== $layoutId) {
                return response()->json([
                    'message' => "Widget {$widgetData['id']} does not belong to layout {$layoutId}",
                ], 422);
            }


            $widget->update([
                'config' => $widgetData['config'] ?? $widget->config,
            ]);

            $updatedWidgets[] = new HomeWidgetResource($widget);
        }


        return response()->json([
            'widgets' => $updatedWidgets,
        ], 200);
    }


    public function batchDestroy(Request $request, int $layoutId)
    {
        $request->validate([
            'widgetIds' => 'required|array',
            'widgetIds.*' => 'integer|exists:home_widgets,id',
        ]);

        $layout = HomeLayout::findOrFail($layoutId);

        $this->authorize('update', $layout);

        $deletedIds = [];

        foreach ($request->widgetIds as $widgetId) {
            $widget = HomeWidget::findOrFail($widgetId);

            // Verify widget belongs to this layout
            if ($widget->home_layout_id !== $layoutId) {
                continue; // Skip widgets that don't belong to this layout
            }


            $widget->delete();
            $deletedIds[] = $widgetId;
        }


        return response()->json([
            'deleted' => $deletedIds,
        ], 200);
    }
}
