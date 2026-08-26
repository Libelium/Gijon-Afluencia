<?php

namespace App\Http\V1\Controllers;

use Illuminate\Support\Facades\Auth;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\Alarms\AlarmActionsRequest;
use App\Http\V1\Requests\Alarms\UpdateAlarmRequest;
use App\Http\V1\Requests\PaginationRequest;
use App\Http\V1\Resources\AlarmActionResource;
use App\Models\Actions\Action;
use App\Models\Actions\ActionEmail;
use App\Models\Actions\ActionPush;
use App\Models\Actions\ActionHttpPush;
use App\Models\Actions\ActionTelegram;
use App\Models\Actions\ActionWhatsapp;
use App\Models\Actions\ActionSms;
use App\Models\Actions\ActionEntityCommand;
use App\Models\Actions\AlarmHasAction;
use App\Models\Alarm;
use App\Models\TelegramUserChat;
use Illuminate\Http\Request;

class AlarmActionController extends Controller
{
    public function index(int $alarmId)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('read', $alarm);

        $alarmActions = AlarmHasAction::where('alarm_id', $alarmId)
            ->with('action')
            ->with('action.actionable')
            ->get();
        return response(['actions' => AlarmActionResource::collection($alarmActions)], 200);
    }

    public function store(AlarmActionsRequest $request)
    {
        $user = Auth::user();

        if (isset($request->actions) && count($request->actions) > 0) {
            foreach ($request->alarm_ids as $alarmId) {
                $alarm = Alarm::where([
                    'id' => $alarmId,
                    'user_id' => $user->id
                ])->firstOrFail();

                $this->authorize('update', $alarm);

                try {
                    foreach ($request->actions as $action) {
                        $actionModel = null;
                        switch ($action['type']) {
                            case 'email':
                                $actionModel = new ActionEmail([
                                    'destination' => $action['to'],
                                    'subject' => $action['subject'],
                                    'content' => $action['body'],
                                ]);
                                break;
                            case 'push':
                                $actionModel = new ActionPush([
                                    'destination_user_id' => $user->id,
                                    'title' => $action['title'],
                                    'content' => $action['content'],
                                ]);
                                break;
                            case 'http_push':
                                $actionModel = new ActionHttpPush([
                                    'url_template' => $action['url_template'],
                                    'method' => $action['method'],
                                    'authorization' => $action['authorization'] ?? null,
                                ]);
                                break;
                            case 'telegram':
                                $telegramChat = TelegramUserChat::where('user_id', $user->id)->firstOrFail();
                                $actionModel = new ActionTelegram([
                                    'chat_id' => $telegramChat->chat_id,
                                    'message' => $action['message'],
                                ]);
                                break;
                            case 'whatsapp':
                                $actionModel = new ActionWhatsapp([
                                    'phone'   => $action['phone'],
                                    'message' => $action['message'],
                                ]);
                                break;
                            case 'sms':
                                $actionModel = new ActionSms([
                                    'phone'   => $action['phone'],
                                    'message' => $action['message'],
                                ]);
                                break;
                            case 'entity_command':
                                $actionModel = new ActionEntityCommand([
                                    'commands' => $action['commands'],
                                    'meta'     => $action['meta'] ?? null,
                                ]);
                                break;
                        }
                        $actionModel->save();
                        $actionIns = new Action([
                            'alarm_id' => $alarm->id,
                            'user_id' => $user->id,
                            'name' => $action['name'] ?? 'Action for ' . $alarm->name,
                        ]);

                        $actionIns = $actionModel->action()->save($actionIns);
                        AlarmHasAction::create([
                            'alarm_id' => $alarm->id,
                            'action_id' => $actionIns->id,
                            'type' => $action['alarm_trigger']
                        ]);
                    }
                } catch (\Exception $e) {
                    return response(['status' => 'error', 'errors' => $e->getMessage()], 500);
                }
            }
        }

        return response(['status' => 'ok'], 201);
    }

    public function destroy(int $alarmId, int $id)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarm->hasActions()->where('action_id', $id)->delete();

        return response('Alarm action deleted', 201);
    }

    /**
     * Deletes all the actions of an alarm and call store to create the new ones
     */
    public function bulkUpdate(int $alarmId, AlarmActionsRequest $request)
    {
        $alarm = Alarm::findOrFail($alarmId);

        $this->authorize('update', $alarm);

        $alarm->hasActions();
        // Get the ids of the actions
        $ids = $alarm->hasActions->pluck('action_id')->toArray();

        // Delete the hasActions
        $alarm->hasActions()->delete();

        // Delete the actions
        Action::destroy($ids);

        // Select orphaned actionables not used in any action
        $actionEmails = ActionEmail::whereDoesntHave('action')->get();
        $actionPushes = ActionPush::whereDoesntHave('action')->get();
        $actionHttpPushes = ActionHttpPush::whereDoesntHave('action')->get();
        $actionTelegrams = ActionTelegram::whereDoesntHave('action')->get();
        $actionWhatsapps = ActionWhatsapp::whereDoesntHave('action')->get();
        $actionSmses = ActionSms::whereDoesntHave('action')->get();
        $actionActionables = ActionEntityCommand::whereDoesntHave('action')->get();

        // Delete orphaned actionables
        ActionEmail::destroy($actionEmails->pluck('id')->toArray());
        ActionPush::destroy($actionPushes->pluck('id')->toArray());
        ActionHttpPush::destroy($actionHttpPushes->pluck('id')->toArray());
        ActionTelegram::destroy($actionTelegrams->pluck('id')->toArray());
        ActionWhatsapp::destroy($actionWhatsapps->pluck('id')->toArray());
        ActionSms::destroy($actionSmses->pluck('id')->toArray());
        ActionEntityCommand::destroy($actionActionables->pluck('id')->toArray());

        $request->merge(['alarm_ids' => [$alarmId]]);

        // Forward the request to store
        return $this->store($request);
    }

    public function channels()
    {
        return response()->json([
            'telegram' => (bool) config('services.telegram.enabled'),
            'sms'      => (bool) config('services.sms.enabled'),
            'whatsapp' => (bool) config('services.whatsapp.enabled'),
        ]);
    }
}
