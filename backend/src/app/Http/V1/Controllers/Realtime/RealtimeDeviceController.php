<?php

namespace App\Http\V1\Controllers\Realtime;

use App\Http\V1\Controllers\Controller;
use App\Models\Device;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use App\Http\V1\Controllers\Realtime\RealtimeEntityController;
use Carbon\Carbon;

class RealtimeDeviceController extends Controller
{
    private RealtimeEntityController $realtimeEntityController;

    public function __construct(RealtimeEntityController $realtimeEntityController)
    {
        $this->realtimeEntityController = $realtimeEntityController;
    }

    private function getDeviceData(string $serial, Request $request): array
    {
        $device = Device::where('serial', $serial)->with('entities')->firstOrFail();

        // Authorization
        $this->authorize('read', $device);

        // Parse request parameters like in RealtimeEntityController::getEntityRequest
        $typeFilter = explode(',', $request->input('attrTypeFilter', 'Property,Relationship,Command'));
        $nameFilter = $request->input('attrNameFilter', '') === '' ? [] : explode(',', $request->input('attrNameFilter', ''));
        $propFilter = $request->input('attrPropFilter', '') === '' ? [] : explode(',', $request->input('attrPropFilter', ''));
        $relFilter = $request->input('attrRelFilter', '') === '' ? [] : explode(',', $request->input('attrRelFilter', ''));
        $cmdFilter = $request->input('attrCmdFilter', '') === '' ? [] : explode(',', $request->input('attrCmdFilter', ''));

        $propFilter = array_merge($propFilter, $nameFilter);
        $relFilter = array_merge($relFilter, $nameFilter);
        $cmdFilter = array_merge($cmdFilter, $nameFilter);

        $lastSent = (bool) $request->input('lastSent', false);
        $filterCmdAvailable = (bool) $request->input('filterCmdAvailable', false);
        $filterCmdPending = (bool) $request->input('filterCmdPending', false);
        $referenceDataNesting = (int) $request->input('referenceDataNesting', 0);

        $allEntitiesData = [];

        foreach ($device->entities as $entity) {
            $entityData = $this->realtimeEntityController->getEntity(
                $entity->urn,
                $entity->tenant,
                $entity->scope,
                $typeFilter,
                $propFilter,
                $relFilter,
                $cmdFilter,
                $lastSent,
                $filterCmdAvailable,
                $filterCmdPending,
                $referenceDataNesting,
                [], // alreadyFetchedList
                false // don't throw error, just return empty array if not found or no permission
            );

            $allEntitiesData = array_merge($allEntitiesData, $entityData);
        }

        return $allEntitiesData;
    }

    public function getDeviceDataRequest(string $serial, Request $request): Response
    {
        $data = $this->getDeviceData($serial, $request);

        $data = array_map(function ($item) {
            return $item->toArray(null);
        }, $data);

        return response($data, 200);
    }
}
