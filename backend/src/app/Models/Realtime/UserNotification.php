<?php

namespace App\Models\Realtime;

use Illuminate\Database\Eloquent\Model;

class UserNotification extends Model
{
    public $timestamps = false;

    protected $connection = 'pgsql_realtime';

    protected $casts = [
        'data' => 'array',
    ];

    protected $fillable = [
        'id',
        'user_id',
        'data',
        'read',
        'updated_at',
        'created_at'
    ];
}