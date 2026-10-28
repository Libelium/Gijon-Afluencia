<?php

namespace App\Http\V1\Controllers\OutConnectors;

use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\PaginationRequest;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Resources\OutConnectors\OutConnectorResource;
use App\Http\V1\Resources\OutConnectors\SimpleOutConnectorResource;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use App\Models\OutConnectors\OutConnector;
use App\Repositories\OutConnectorRepository;
use App\Repositories\ResourcePermissionRepository;
use App\Models\Device;
use App\Models\Entity;

class OutConnectorController extends Controller
{
    public function show(int $id)
    {
        $outConnector = OutConnector::with(['connectable', 'entities', 'devices'])->findOrFail($id);

        $this->authorize('read', $outConnector);

        return (new OutConnectorResource($outConnector))->response();
    }

    public function paginate(PaginationRequest $request)
    {
        $this->authorize('list', OutConnector::class);

        $out_connectors = OutConnectorRepository::paginate(
            Auth::user()->id,
            $request->input('paginationSize', 10),
            $request->input('page', 1),
            $request->input('orderBy'),
            $request->boolean('orderDirection') ? 'desc' : 'asc',
            $request->input('search')
        );

        $result = [
            'rows' => SimpleOutConnectorResource::collection($out_connectors['rows']),
            'count' => $out_connectors['count'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    /**
     * Activates or deactivates the connector. Activating clears the failure count, so a
     * connector the worker deactivated after repeated failures starts again from zero.
     */
    public function updateStatus(int $id, Request $request)
    {
        $outConnector = OutConnector::with('connectable')->findOrFail($id);

        $this->authorize('update', $outConnector);

        $request->validate([
            'status' => 'required|string|in:active,inactive',
        ]);

        $values = ['status' => $request->input('status')];
        if ($values['status'] === 'active') {
            $values['retries'] = 0;
        }
        $outConnector->forceFill($values)->save();

        return (new OutConnectorResource($outConnector))->response();
    }

    public function destroy(int $id): Response
    {
        $outConnector = OutConnector::with('connectable')->findOrFail($id);

        $this->authorize('delete', $outConnector);

        // out_connectors_has_models goes with the connector through its cascading foreign key.
        DB::transaction(function () use ($outConnector) {
            $connectable = $outConnector->connectable;
            ResourcePermissionRepository::deleteModelWithResourcePermissions($outConnector);
            $connectable?->delete();
        });

        return response(null, 204);
    }

    /**
     * Replaces the entities and devices whose data the connector forwards. A list left out of
     * the request keeps its current links.
     */
    public function linkModelsByConnectorId(int $outConnectorId, Request $request): Response
    {
        $outConnector = OutConnector::findOrFail($outConnectorId);

        $this->authorize('update', $outConnector);

        $request->validate([
            'entities' => 'sometimes|array',
            'entities.*' => 'integer',
            'devices' => 'sometimes|array',
            'devices.*' => 'integer',
        ]);

        // Authorize everything before touching the links, so a refusal leaves them as they were.
        $entityIds = $request->has('entities') ? $this->authorizedIds(Entity::class, $request->input('entities')) : null;
        $deviceIds = $request->has('devices') ? $this->authorizedIds(Device::class, $request->input('devices')) : null;

        DB::transaction(function () use ($outConnector, $entityIds, $deviceIds) {
            if ($entityIds !== null) {
                $outConnector->entities()->sync($entityIds);
            }
            if ($deviceIds !== null) {
                $outConnector->devices()->sync($deviceIds);
            }
        });

        return response(null, 204);
    }

    private function authorizedIds(string $modelClass, array $ids): array
    {
        $models = $modelClass::findOrFail(array_unique($ids));

        foreach ($models as $model) {
            $this->authorize('read', $model);
        }

        return $models->pluck('id')->all();
    }
}
