<?php

namespace App\Repositories\Realtime;

use App\Models\Realtime\UserNotification;

//use Illuminate\Support\Facades\Auth;

class UserNotificationRepository
{

  public static function getCountByUser($user_id, $read)
  {

    $count = UserNotification::select()
      ->where('user_id', $user_id)
      ->where('read', $read)
      ->count();

    return $count;
  }

  public static function getByUser($user_id, $read)
  {
    $data = UserNotification::select()
      ->where('user_id', $user_id)
      ->where('read', $read)
      ->orderBy('created_at', 'desc')
      ->get();

    return $data;
  }

}
