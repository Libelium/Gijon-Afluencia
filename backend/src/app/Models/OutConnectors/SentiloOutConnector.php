<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class SentiloOutConnector extends AuditableModel
{
    protected $table = 'sentilo_out_connector';

    protected $fillable = [
        'sensor_id_template',
        'identity_key',
        'url',

    ];

    protected $casts = [
        'sensor_id_template' => 'array',
    ];

    public function getMorphClass()
    {
        return $this->table;
    }

    public function out_connector()
    {
        return $this->morphOne(OutConnector::class, 'connectable');
    }
}
