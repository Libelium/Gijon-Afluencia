<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class InactivityAlarmCondition extends AuditableModel
{
    protected $fillable = [
        'alarm_id',
        'entity_id',
        'measure',
        'timeout_s'
    ];

    public function alarm()
    {
        return $this->belongsTo(\App\Models\Alarm::class);
    }

    public function entity()
    {
        return $this->belongsTo(\App\Models\Entity::class);
    }
}
