<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AlarmCondition extends AuditableModel
{
    protected $fillable = [
        'alarm_id',
        'entity_id',
        'measure',
        'condition',
        'threshold',
        'period',
    ];

    protected $casts = [
        'period' => 'array',
    ];

    public function alarm()
    {
        return $this->belongsTo(\App\Models\Alarm::class);
    }

    public function entity()
    {
        return $this->belongsTo(\App\Models\Entity::class);
    }

    public function getThresholdAttribute($value)
    {
        return explode("#", $value);
    }

    public function setThresholdAttribute($value)
    {
        $this->attributes['threshold'] = implode("#", $value);
    }
}
