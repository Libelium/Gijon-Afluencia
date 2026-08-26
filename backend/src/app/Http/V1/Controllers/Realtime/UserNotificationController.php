<?php

namespace App\Http\V1\Controllers\Realtime;

use App\Http\V1\Controllers\Controller;
use App\Models\Realtime\UserNotification;
use App\Repositories\Realtime\UserNotificationRepository;
use Illuminate\Support\Facades\Auth;

use Illuminate\Http\Request;

class UserNotificationController extends Controller
{
    public function getData()
    {
        $records = UserNotificationRepository::getByUser(Auth::id(), false);
        return response(['data' => $records], 200);
    }
    public function readAll()
    {
        $records = UserNotification::where('user_id', Auth::id())->update(['read' => true]);
        return response(['data' => $records], 200);
    }
    public function countData()
    {
        $records = UserNotificationRepository::getCountByUser(Auth::id(), false);
        return response(['data' => $records], 200);
    }
    public function updateRead(int $id)
    {
        $records = UserNotification::where('id', $id)->where('user_id', Auth::id())->findOrFail($id);
        
        if ($records) {
            $records->update(['read' => true]);
        }

        return response(['data' => $records], 200);
    }
    public function deleteNotification(int $id)
    {
        $records = UserNotification::where('id', $id)->where('user_id', Auth::id())->findOrFail($id);
        
        if ($records) {
            $records->delete();
        }

        return response(['data' => $records], 200);
    }
}
