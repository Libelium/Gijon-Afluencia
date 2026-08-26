<?php

namespace App\Http\V1\Controllers;

use Illuminate\Support\Facades\Auth;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Resources\InactivityAlarmConditionResource;
use App\Models\Alarm;
use App\Models\InactivityAlarmCondition;
use App\Http\V1\Requests\Alarms\InactivityAlarmConditionRequest;
use App\Http\V1\Requests\Alarms\UpdateInactivityAlarmConditionRequest;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class InactivityAlarmConditionController extends Controller
{
    public function index(int $alarmId)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('read', $alarm);

        $alarmCondition = InactivityAlarmCondition::select(
            'inactivity_alarm_conditions.*',
            'entities.datamodel as datamodel',
            'entities.urn as entity_urn',
            'entities.tenant as tenant',
            'entities.scope as scope'
        )->join('alarms', 'alarms.id', '=', 'inactivity_alarm_conditions.alarm_id')
            ->join('entities', 'entities.id', '=', 'inactivity_alarm_conditions.entity_id')
            ->where([
                'alarms.id' => $alarmId,
                'alarms.type' => 'inactivity'
            ])
            ->get();
        return response(InactivityAlarmConditionResource::collection($alarmCondition), 200);
    }

    public function show(int $alarmId, int $id)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('read', $alarm);

        $alarmCondition = InactivityAlarmCondition::select('inactivity_alarm_conditions.*')
            ->join('alarms', 'alarms.id', '=', 'inactivity_alarm_conditions.alarm_id')
            ->where([
                'inactivity_alarm_conditions.id' => $id,
                'alarms.id' => $alarmId,
                'alarms.user_id' => Auth::id(),
                'alarms.type' => 'inactivity'
            ])
            ->firstOrFail();

        return response(new InactivityAlarmConditionResource($alarmCondition), 200);
    }

    public function store(InactivityAlarmConditionRequest $request, int $alarmId)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmCondition = new InactivityAlarmCondition($request->toModel() + ['alarm_id' => $alarm->id]);

        try {
            $alarmCondition->save();
            return response(new InactivityAlarmConditionResource($alarmCondition), 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (store)'], 500);
        }
    }

    public function update(UpdateInactivityAlarmConditionRequest $request, int $alarmId, int $id)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmCondition = InactivityAlarmCondition::where([
            ['id', $id],
            ['alarm_id', $alarmId],
        ])->firstOrFail();

        $alarmCondition->fill($request->toModel());
        try {
            $alarmCondition->save();
            return response(new InactivityAlarmConditionResource($alarmCondition), 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (update)'], 500);
        }
    }

    public function bulkUpdate(Request $request, int $alarmId)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmConditions = $alarm->inactivityConditions;

        foreach ($alarmConditions as $alarmCondition) {
            if (!in_array($alarmCondition->id, array_column($request->conditions, 'id'))) {
                $alarmCondition->delete();
            }
        }

        foreach ($request->conditions as $condition) {
            $conditionContent = [
                'entity_id' => $condition['entity']['id'],
                'timeout_s' => $condition['timeoutS'],
                'measure' => $condition['measure']
            ];
            if (isset($condition['id'])) {
                $alarmCondition = InactivityAlarmCondition::where([
                    ['id', $condition['id']],
                    ['alarm_id', $alarmId]
                ])->firstOrFail();
                $alarmCondition->fill($conditionContent);
                $alarmCondition->save();
            } else {
                $alarmCondition = new InactivityAlarmCondition([
                    'alarm_id' => $alarm->id,
                ] + $conditionContent);
                $alarmCondition->save();
            }
        }
    }


    public function destroy(int $alarmId, int $id): Response
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        try {
            $alarm->inactivityConditions()->where('id', $id)->firstOrFail()->delete();
            return response('Inactivity Condition deleted', 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (delete)'], 500);
        }
    }
}
