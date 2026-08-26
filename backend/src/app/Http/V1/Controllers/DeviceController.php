<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Requests\PaginationRequest;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Repositories\DeviceRepository;
use App\Http\V1\Resources\DeviceResource;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Models\Device;
use App\Models\Entity;


class DeviceController extends Controller
{

    public function show(int $id)
    {
        $device = Device::with([
            'deviceType',
            'entities' => function ($query) {
                $query->select('entities.id');
            },
            'mainEntity.geolocation'
        ])
            ->findOrFail($id);

        if (!$device) {
            return response('Device not found', 404);
        }

        $this->authorize('read', $device);

        return (new DeviceResource($device))->response();
    }

    public function paginate(PaginationRequest $request)
    // public function paginate(Request $request)
    {
        $this->authorize('list', Device::class);

        $paginationSize = $request->input('paginationSize', '10');
        $page = $request->input('page', 1);
        $orderColumn = $request->input('orderBy', 'devices.id');
        $orderDirection = $request->input('orderDirection', true) == true ? 'desc' : 'asc';
        $searchText = $request->input('search', '');
        $realtimeProperties = $request->input('realtimeProperties', []);

        $paginationResult = DeviceRepository::paginate(
            Auth::user()->id,
            $paginationSize,
            $page,
            $orderColumn,
            $orderDirection,
            $searchText,
            $realtimeProperties
        );

        $result = [
            'count' => $paginationResult->total(),
            'rows' => DeviceResource::collection($paginationResult->items()),
            'items' => $paginationResult->items(),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function getEntities(int $id): Response
    {
        $device = Device::with('entities')->findOrFail($id);

        $this->authorize('read', $device);

        return response($device->entities->pluck('id')->toArray(), 200);
    }

    public function devicesByEntityIds(Request $request)
    {
        $entityIds = $request->input('entity_ids', []);

        if (empty($entityIds)) {
            return response()->json([]);
        }

        $entities = Entity::whereIn('id', $entityIds)->get();
        foreach ($entities as $entity) {
            $this->authorize('read', $entity);
        }

        $rows = DB::table('device_entity')
            ->whereIn('entity_id', $entityIds)
            ->select('device_id', 'entity_id')
            ->get();

        $deviceIds = $rows->pluck('device_id')->unique()->all();

        $devices = Device::whereIn('id', $deviceIds)
            ->with('mainEntity')
            ->get()
            ->keyBy('id');

        $data = $rows->map(function ($row) use ($devices) {
            $device = $devices->get($row->device_id);
            if (!$device) return null;

            $mainEntity = $device->mainEntity->first();

            return [
                'entity_id' => $row->entity_id,
                'device' => [
                    'id'          => $device->id,
                    'name'        => $device->name,
                    'serial'      => $device->serial,
                    'main_entity' => $mainEntity ? [
                        'urn'    => $mainEntity->urn,
                        'tenant' => $mainEntity->tenant,
                        'scope'  => $mainEntity->scope,
                    ] : null,
                ],
            ];
        })->filter()->values();

        return response()->json($data);
    }
}
