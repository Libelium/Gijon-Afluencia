<?php

namespace App\Http\V1\Controllers;

use App\Models\Dashboard;
use App\Models\Panel;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Resources\PanelResource;
use App\Repositories\PanelRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class PanelController extends Controller
{
    /**
     * Lists the panels of one dashboard.
     *
     * The dashboard is mandatory and is authorized before anything is read: panels carry no
     * permissions of their own, so the owning dashboard is what decides who may see them.
     * It is taken from the request because the route (`apiResource('panels')`) carries no
     * path parameter for it.
     */
    public function index(Request $request)
    {
        $request->validate([
            'dashboard_id' => 'required|numeric',
        ]);

        $dashboard = Dashboard::findOrFail($request->input('dashboard_id'));

        $this->authorize('read', $dashboard);

        $panels = Panel::where('dashboard_id', $dashboard->id)->get();

        return response()->json($panels, 200);
    }

    public function store(Request $request)
    {
        $request->validate([
            'title' => 'nullable|string|max:255',
            'chart.title' => 'required|string|max:255|min:3',
            'chart.type' => 'required|string|max:255|min:3',
            'dashboard_id' => 'required|numeric',
            'series' => 'nullable|array',
            'annotations' => 'nullable|array',
            'annotations.*.datamodel' => 'nullable|string',
            'annotations.*.measure' => 'nullable|string',
            'relativeTime' => 'nullable|boolean',
            'dateRange' => 'nullable|array',
        ]);

        // A panel may only be added to a dashboard the user is allowed to edit.
        $this->authorize('create', [Panel::class, Dashboard::findOrFail($request->dashboard_id)]);

        PanelRepository::validatePanel($request);

        $panel = PanelRepository::store($request);

        return (new PanelResource($panel))->response();
    }

    public function show($id)
    {
        $panel = Panel::findOrFail($id);

        $this->authorize('read', $panel);

        return response()->json($panel, 200);
    }

    public function update(Request $request, $id)
    {
        $request->validate([
            'title' => 'nullable|string|max:255',
            'chart.title' => 'required|string|max:255|min:3',
            'chart.type' => 'required|string|max:255|min:3',
            'dashboard_id' => 'required|numeric',
            'series' => 'nullable|array',
            'annotations' => 'nullable|array',
            'annotations.*.datamodel' => 'nullable|string',
            'annotations.*.measure' => 'nullable|string',
            'relativeTime' => 'nullable|boolean',
            'dateRange' => 'nullable|array',
        ]);

        $panel = Panel::findOrFail($id);

        // Both ends are authorized: the dashboard the panel is in today, and the one the
        // request wants to move it to. Checking only the source would let a user push a panel
        // into somebody else's dashboard.
        $this->authorize('update', $panel);
        $this->authorize('create', [Panel::class, Dashboard::findOrFail($request->dashboard_id)]);

        PanelRepository::validatePanel($request);

        $panel = PanelRepository::update($request, $id);

        return (new PanelResource($panel))->response();
    }


    public function destroy($id)
    {
        $panel = Panel::findOrFail($id);

        $this->authorize('delete', $panel);

        try {
            $image = Storage::disk('s3images')->exists('/dashboard/panel' . $id);

            if ($image) {
                Storage::disk('s3images')->delete('/dashboard/panel' . $id);
            }
        } catch (\Exception $e) {
            // pass: skip the exception
        }

        $panel->delete();

        return response()->json($panel, 200);
    }

    public function setImage(Request $request, $id)
    {
        $request->validate([
            'image' => 'required|image|mimes:jpeg,png,jpg,gif,svg|max:2048',
        ]);

        $panel = Panel::findOrFail($id);

        $this->authorize('update', $panel);

        $image = Storage::disk('s3images')->put('/dashboard/panel' . $id . '/plan', file_get_contents($request->image));

        if (!$image) {
            return response()->json([
                'message' => 'Error uploading image',
            ], 500);
        }

        return response()->json([
            'message' => 'Image uploaded successfully',
            'image' => $image,
        ], 200);
    }

    public function getImage($id)
    {
        $panel = Panel::findOrFail($id);

        $this->authorize('read', $panel);

        $exists_image = Storage::disk('s3images')->exists('/dashboard/panel' . $id . '/plan');

        if (!$exists_image) {
            return response()->json([
                'message' => 'Image not found',
            ], 404);
        }

        $image = Storage::disk('s3images')->get('/dashboard/panel' . $id . '/plan');

        $base64 = base64_encode($image);

        return response()->json([
            'image' => $base64,
        ], 200);
    }
}
