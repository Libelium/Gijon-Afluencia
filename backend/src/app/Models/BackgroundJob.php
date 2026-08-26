<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class BackgroundJob extends Model
{
    protected $table = 'background_jobs';

    protected $fillable = [
        'user_id',
        'name',
        'type',
        'status',
        'params',
        'total_steps',
        'started_at',
        'completed_at',
    ];

    protected $casts = [
        'params' => 'array',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
    ];
}
