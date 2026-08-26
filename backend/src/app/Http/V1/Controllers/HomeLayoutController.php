<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Resources\HomeLayoutResource;
use App\Models\HomeLayout;
use App\Repositories\HomeLayoutRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class HomeLayoutController extends Controller
{
    public function index()
    {
        $this->authorize('list', HomeLayout::class);

        $layouts = HomeLayoutRepository::getForUser();

        return response()->json($layouts, 200);
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'string|max:255|nullable',
            'layout' => 'array|nullable',
            'responsiveLayout' => 'array|nullable',
        ]);

        $this->authorize('create', HomeLayout::class);

        $layout = HomeLayout::create([
            'user_id' => Auth::id(),
            'name' => $request->name,
            'layout' => $request->layout ?? [],
            'responsive_layout' => $request->responsiveLayout,
        ]);

        return new HomeLayoutResource($layout);
    }

    public function show(int $id)
    {
        $layout = HomeLayout::with('widgets')->findOrFail($id);

        $this->authorize('read', $layout);

        return response()->json($layout, 200);
    }

    public function update(Request $request, int $id)
    {
        $request->validate([
            'name' => 'string|max:255',
            'layout' => 'array|nullable',
            'responsiveLayout' => 'array|nullable',
        ]);

        $layout = HomeLayout::findOrFail($id);

        $this->authorize('update', $layout);

        $updateData = [];

        if ($request->has('name')) {
            $updateData['name'] = $request->name;
        }

        if ($request->has('layout')) {
            $updateData['layout'] = $request->layout;
        }

        if ($request->has('responsiveLayout')) {
            $updateData['responsive_layout'] = $request->responsiveLayout;
        }

        if (!empty($updateData)) {
            $layout->update($updateData);
        }

        return response()->json($layout, 200);
    }

    public function destroy(int $id)
    {
        $layout = HomeLayout::findOrFail($id);

        $this->authorize('delete', $layout);

        $layout->delete();

        return response()->json(true, 200);
    }

    /**
     * Atomically create a default layout with widgets
     * This endpoint creates the layout, creates its widgets, and updates the layout
     * with the proper widget IDs - all in one request to avoid race conditions
     */
    public function createDefaultLayout(Request $request)
    {
        $request->validate([
            'name' => 'string|max:255|nullable',
            'layout' => 'array|required',
            'responsiveLayout' => 'array|nullable',
            'widgets' => 'required|array',
            'widgets.*.type' => 'required|string|max:32',
            'widgets.*.config' => 'array|nullable',
            'widgets.*.id' => 'integer|nullable',
        ]);

        $this->authorize('create', HomeLayout::class);

        // Step 1: Create the layout with empty layout arrays
        $layout = HomeLayout::create([
            'user_id' => Auth::id(),
            'name' => $request->name,
            'layout' => [],
            'responsive_layout' => $request->responsiveLayout ?? [],
        ]);

        // Step 2: Create widgets
        $createdWidgets = [];
        foreach ($request->widgets as $widgetData) {
            $widget = \App\Models\HomeWidget::create([
                'user_id' => Auth::id(),
                'home_layout_id' => $layout->id,
                'type' => $widgetData['type'],
                'config' => $widgetData['config'] ?? null,
            ]);
            $createdWidgets[] = $widget;
        }

        // Step 3: Map old widget IDs to new widget IDs
        $idMap = [];
        foreach ($request->widgets as $index => $widgetData) {
            if (isset($widgetData['id']) && isset($createdWidgets[$index])) {
                $idMap[$widgetData['id']] = $createdWidgets[$index]->id;
            }
        }

        // Step 4: Update layout items with new widget IDs
        $updatedLayout = $this->remapLayoutIds($request->layout, $idMap);
        $updatedResponsiveLayout = [];
        if ($request->responsiveLayout) {
            foreach ($request->responsiveLayout as $breakpoint => $items) {
                $updatedResponsiveLayout[$breakpoint] = $this->remapLayoutIds($items, $idMap);
            }
        }

        // Step 5: Update the layout with the remapped IDs
        $layout->update([
            'layout' => $updatedLayout,
            'responsive_layout' => $updatedResponsiveLayout,
        ]);

        // Step 6: Load widgets and return complete layout
        $layout->load('widgets');

        return new HomeLayoutResource($layout);
    }

    /**
     * Helper function to remap layout item IDs
     */
    private function remapLayoutIds(array $layoutItems, array $idMap): array
    {
        return array_map(function ($item) use ($idMap) {
            if (isset($item['i']) && isset($idMap[(int)$item['i']])) {
                $item['i'] = (string)$idMap[(int)$item['i']];
            }
            return $item;
        }, $layoutItems);
    }
}
