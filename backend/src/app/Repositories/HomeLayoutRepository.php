<?php

namespace App\Repositories;

use App\Models\HomeLayout;
use Illuminate\Support\Facades\Auth;

class HomeLayoutRepository
{
    public static function getForUser()
    {
        $userId = Auth::id();

        return HomeLayout::query()
            ->where('user_id', $userId)
            ->with('widgets')
            ->get();
    }
}
