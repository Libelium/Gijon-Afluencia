<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Http\V1\Resources\TagResource;
use App\Models\Tag;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class TagController extends Controller
{
    public function index()
    {
        $user = Auth::user();

        if (!$user->can(AppPermission::DASHBOARDS_READ->value)) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $tags = Tag::where('organization_id', $user->organization_id)
            ->orderBy('name')
            ->get();

        return TagResource::collection($tags);
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:100',
            'color' => 'string|max:30|nullable',
        ]);

        $user = Auth::user();

        if (!$user->can(AppPermission::DASHBOARDS_UPDATE->value)) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $tag = Tag::create([
            'name' => $request->name,
            'color' => $request->color,
            'organization_id' => $user->organization_id,
        ]);

        return new TagResource($tag);
    }

    public function update(Request $request, int $id)
    {
        $request->validate([
            'name' => 'string|max:100',
            'color' => 'string|max:30|nullable',
        ]);

        $user = Auth::user();

        if (!$user->can(AppPermission::DASHBOARDS_UPDATE->value)) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $tag = Tag::where('id', $id)
            ->where('organization_id', $user->organization_id)
            ->firstOrFail();

        $tag->update([
            'name' => $request->name ?? $tag->name,
            'color' => $request->color ?? $tag->color,
        ]);

        return new TagResource($tag);
    }

    public function destroy(int $id)
    {
        $user = Auth::user();

        if (!$user->can(AppPermission::DASHBOARDS_UPDATE->value)) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $tag = Tag::where('id', $id)
            ->where('organization_id', $user->organization_id)
            ->firstOrFail();

        $tag->delete();

        return response()->json(true, 200);
    }

    public function modificationsInBatch(Request $request)
    {
        $request->validate([
            'create' => 'array',
            'create.*.name' => 'required|string|max:100',
            'create.*.color' => 'string|max:30|nullable',
            'update' => 'array',
            'update.*.id' => 'required|integer',
            'update.*.name' => 'required|string|max:100',
            'update.*.color' => 'string|max:30|nullable',
            'delete' => 'array',
            'delete.*.id' => 'required|integer',
        ]);

        $user = Auth::user();

        if (!$user->can(AppPermission::DASHBOARDS_UPDATE->value)) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $organizationId = $user->organization_id;

        // Process deletes
        if ($request->has('delete')) {
            $deleteIds = collect($request->delete)->pluck('id');
            Tag::where('organization_id', $organizationId)
                ->whereIn('id', $deleteIds)
                ->delete();
        }

        // Process updates
        if ($request->has('update')) {
            foreach ($request->update as $data) {
                Tag::where('id', $data['id'])
                    ->where('organization_id', $organizationId)
                    ->update([
                        'name' => $data['name'],
                        'color' => $data['color'] ?? null,
                    ]);
            }
        }

        // Process creates
        if ($request->has('create')) {
            foreach ($request->create as $data) {
                Tag::create([
                    'name' => $data['name'],
                    'color' => $data['color'] ?? null,
                    'organization_id' => $organizationId,
                ]);
            }
        }

        $tags = Tag::where('organization_id', $organizationId)
            ->orderBy('name')
            ->get();

        return TagResource::collection($tags);
    }
}
