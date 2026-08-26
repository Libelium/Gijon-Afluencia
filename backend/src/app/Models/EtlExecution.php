<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class EtlExecution extends Model
{
    protected $table = 'etl_executions';

    protected $fillable = [
        'type',
        'user_id',
        'execution_date',
        'params',
    ];

    protected $casts = [
        'params' => 'array',
        'execution_date' => 'date',
    ];

    public function user(): \Illuminate\Database\Eloquent\Relations\BelongsTo
    {
        return $this->belongsTo(\App\Models\User::class);
    }
}
