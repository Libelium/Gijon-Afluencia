<?php

namespace App\Http\V1\Controllers;

use App\Models\Panel;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Resources\PanelResource;
use App\Repositories\PanelRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class PanelController extends Controller
{
    public function index($dashboard_id)
    {
        $panels = Panel::where('dashboard_id', $dashboard_id)->get();

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

        PanelRepository::validatePanel($request);

        $panel = PanelRepository::store($request);

        return (new PanelResource($panel))->response();
    }

    public function show($id)
    {
        $panel = Panel::findOrFail($id);

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

        PanelRepository::validatePanel($request);

        $panel = PanelRepository::update($request, $id);

        return (new PanelResource($panel))->response();
    }


    public function destroy($id)
    {
        $panel = Panel::findOrFail($id);

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

        Panel::findOrFail($id);

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
