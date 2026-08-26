<?php

namespace App\Http\V1\Controllers;

use Illuminate\Support\Facades\Auth;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\Alarms\AlarmConditionRequest;
use App\Http\V1\Requests\Alarms\UpdateAlarmConditionRequest;
use App\Http\V1\Resources\AlarmConditionResource;
use App\Models\Alarm;
use App\Models\AlarmCondition;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class AlarmConditionController extends Controller
{
    public function index(int $alarmId)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('read', $alarm);

        $alarmCondition = AlarmCondition::select('alarm_conditions.*', 'entities.datamodel as datamodel', 'entities.urn as entity_urn', 'entities.tenant as tenant', 'entities.scope as scope')
            ->join('alarms', 'alarms.id', '=', 'alarm_conditions.alarm_id')
            ->join('entities', 'entities.id', '=', 'alarm_conditions.entity_id')
            ->where([
                'alarms.id' => $alarmId,
                'alarms.type' => 'basic'
            ])
            ->get();
        return response(AlarmConditionResource::collection($alarmCondition), 200);
    }

    public function show(int $alarmId, int $id)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('read', $alarm);

        $alarmCondition = AlarmCondition::select('alarm_conditions.*')
            ->join('alarms', 'alarms.id', '=', 'alarm_conditions.alarm_id')
            ->where([
                'alarm_conditions.id' => $id,
                'alarms.id' => $alarmId,
                'alarms.user_id' => Auth::id(),
                'alarms.type' => 'basic'
            ])
            ->firstOrFail();

        return response(new AlarmConditionResource($alarmCondition), 200);
    }

    public function store(AlarmConditionRequest $request, int $alarmId)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmCondition = new AlarmCondition(['alarm_id' => $alarm->id,] + $request->all());

        try {
            $alarmCondition->save();
            return response(new AlarmConditionResource($alarmCondition), 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (store)'], 500);
        }
    }

    public function update(UpdateAlarmConditionRequest $request, int $alarmId, int $id)
    {

        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmCondition = AlarmCondition::where([
            ['id', $id],
            ['alarm_id', $alarmId]
        ])->firstOrFail();

        $alarmCondition->fill($request->all());
        try {
            $alarmCondition->save();
            return response(new AlarmConditionResource($alarmCondition), 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (update)'], 500);
        }
    }


    public function destroy(int $alarmId, int $id): Response
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        try {
            $alarm->conditions()->where('id', $id)->firstOrFail()->delete();
            return response('AlarmCondition deleted', 201);
        } catch (\Exception $e) {
            return response(['errors' => 'The operation couldn’t be completed (delete)'], 500);
        }
    }

    /**
     *
     * This method is used to update all the conditions on the report
     * update if exist, create if not, delete if not in the request
     */
    public function bulkUpdate(int $alarmId, Request $request): Response
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarmConditions = $alarm->conditions;
        // Delete conditions that are not in the request
        foreach ($alarmConditions as $alarmCondition) {
            if (!in_array($alarmCondition->id, array_column($request->conditions, 'id'))) {
                $alarmCondition->delete();
            }
        }

        foreach ($request->conditions as $condition) {
            $conditionContent = [
                'condition' => $condition['condition'],
                'entity_id' => $condition['entity']['id'],
                'measure' => $condition['measure']['id'],
                'threshold' => $condition['threshold'],
                'period' => $condition['period']
            ];
            if (isset($condition['id'])) {
                $alarmCondition = AlarmCondition::where([
                    ['id', $condition['id']],
                    ['alarm_id', $alarmId]
                ])->firstOrFail();
                $alarmCondition->fill($conditionContent);
                $alarmCondition->save();
            } else {
                $alarmCondition = new AlarmCondition([
                    'alarm_id' => $alarm->id,
                ] + $conditionContent);
                $alarmCondition->save();
            }
        }

        return response('AlarmCondition updated', 201);
    }
}
