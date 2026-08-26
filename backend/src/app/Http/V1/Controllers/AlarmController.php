<?php

namespace App\Http\V1\Controllers;

use App\Models\EntityGroup;
use Illuminate\Support\Facades\Auth;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\Alarms\AlarmRequest;
use App\Http\V1\Requests\Alarms\UpdateAlarmRequest;
use App\Http\V1\Requests\PaginationRequest;
use App\Http\V1\Resources\AlarmResource;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Models\Alarm;
use App\Models\Entity;
use App\Repositories\AlarmRepository;
use Illuminate\Http\Request;
use App\Repositories\ResourcePermissionRepository;
use App\Repositories\OrganizationRepository;
use App\Authorization\AppResourcePermission;

class AlarmController extends Controller
{
    public function paginate(PaginationRequest $request)
    {
        $paginationSize = $request->input('paginationSize', '10');
        $page = $request->input('page', 0);
        $orderColumn = $request->input('orderBy', 'alarms.id');
        $orderDirection = $request->input('sortDesc') ? 'DESC' : 'ASC';
        $search = $request->input('search');

        $alarms = AlarmRepository::paginate(Auth::user()->id, $paginationSize, $page, $orderColumn, $orderDirection, $search);

        $result = [
            'count' => $alarms['count'],
            'rows' => $alarms['rows'],
            'items' => $alarms['rows'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function show(Request $request, int $id)
    {
        $request->validate([
            'loadConditions' => 'nullable|string|in:true,false',
        ]);

        $alarm = Alarm::where('id', $id)
            ->with('conditions.entity', 'inactivityConditions.entity')
            ->firstOrFail();

        $this->authorize('read', $alarm);

        return (new AlarmResource($alarm))->response()->setStatusCode(200);
    }

    public function store(AlarmRequest $request)
    {
        if ($request->has('entity_group_id')) {
            $groupId = $request->input('entity_group_id');

            $entityGroup = EntityGroup::with('entities')->findOrFail($groupId);

            $this->authorize('read', $entityGroup);

            $entityRequest = $request->all();

            $base_name = $entityRequest['name'] ?? 'Alarm';

            $created_alarms = [];
            foreach ($entityGroup->entities as $entity) {
                foreach ($entityRequest['conditions'] as $key => $condition) {
                    $entityRequest['conditions'][$key]['entityId'] = $entity->id;
                }


                $entity_name = $entity->urn
                    ? explode(':', $entity->urn)[count(explode(':', $entity->urn)) - 1]
                    : '';

                $entityRequest['name'] = $base_name . ' - ' . $entity_name;

                $alarm = $this->createAlarmWithConditions(new AlarmRequest($entityRequest));

                $created_alarms[] = $alarm;
            }

            if (count($created_alarms) > 1) {
                return response(AlarmResource::collection($created_alarms), 201);
            } else {
                return response(new AlarmResource($alarm), 201);
            }
        }

        $alarm = $this->createAlarmWithConditions($request);

        return response(new AlarmResource($alarm), 201);
    }

    private function createAlarmWithConditions($request)
    {
        # validate that the user can create an alarm
        $this->authorize('create', Alarm::class);

        $alarm = new Alarm([
            'user_id' => Auth::id(),
        ]);
        $alarm->fill($request->all());
        try {
            $alarm->save();
        } catch (\Exception $e) {
            return response(['errors' => 'The alarm can\'t be saved'], 500);
        }

        try {

            $this->createConditions($request, $alarm);
            OrganizationRepository::assignResourceToOrganization(Auth::user()->organization_id, $alarm);

            $default_permissions = AppResourcePermission::defaultPermissions();
            Auth::user()->giveResourcePermissionsTo($default_permissions, $alarm, true);

        } catch (\Exception $e) {
            # rollback
            $alarm->delete();
            return response(['errors' => 'The conditions couldn\'t be saved'], 500);
        }

        return $alarm;
    }

    private function createConditions(AlarmRequest $request, Alarm $alarm)
    {
        switch ($request->type) {
            case 'basic':
                $this->createBasicConditions($request->conditions, $alarm);
                break;

            case 'inactivity':
                $this->createInactivityConditions($request->conditions, $alarm);
                break;

            default:
                throw new \Exception('The type field is invalid, allowed: basic, inactivity');
        }
    }

    private function createBasicConditions(array $basicConditions, Alarm $alarm)
    {
        $conditions = [];
        foreach ($basicConditions as $condition) {

            $entity = Entity::findOrfail($condition['entityId']);

            $this->authorize('read', $entity);

            $newCondition = [
                'alarm_id' => $alarm->id,
                'entity_id' => $condition['entityId'],
                'measure' => $condition['measure'],
                'condition' => $condition['condition'],
                'threshold' => $condition['threshold'],
            ];

            if (isset($condition['period'])) {
                $newCondition['period'] = $condition['period'];
            }

            $conditions[] = $newCondition;
        }

        $alarm->conditions()->createMany($conditions);
    }


    private function createInactivityConditions(array $inactivityConditions, Alarm $alarm)
    {
        $conditions = [];
        foreach ($inactivityConditions as $condition) {

            $entity = Entity::findOrfail($condition['entityId']);
            $this->authorize('read', $entity);

            $newCondition = [
                'alarm_id' => $alarm->id,
                'entity_id' => $condition['entityId'],
                'timeout_s' => $condition['timeoutS'],
            ];

            if (isset($condition['measure'])) {
                $newCondition['measure'] = $condition['measure'];
            }

            $conditions[] = $newCondition;
        }

        $alarm->inactivityConditions()->createMany($conditions);
    }


    public function update(UpdateAlarmRequest $request, $id)
    {
        $alarm = Alarm::findOrfail($id);

        $this->authorize('update', $alarm);

        $alarm->fill($request->all());

        try {
            $alarm->save();
            return response('Alarm Updated', 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (update)'], 500);
        }
    }


    public function destroy($id)
    {
        $alarm = Alarm::findOrfail($id);

        $this->authorize('delete', $alarm);

        try {
            // Delete the different conditions
            $alarm->conditions()->delete();
            $alarm->inactivityConditions()->delete();

            // Delete the actions
            $alarm->hasActions()->delete();

            ResourcePermissionRepository::deleteAllPermissionsForResource($alarm);
            OrganizationRepository::unassignResourceFromAnyOrganization($alarm);
            $alarm->delete();

            return response('Alarm deleted', 200);

        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (delete)'], 500);
        }
    }
}
