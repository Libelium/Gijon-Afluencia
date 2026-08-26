<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Model;

class HttpConnector extends OutConnector
{
    protected $table = 'http_connector';

    protected $fillable = [
        'method',
        'url',
        'headers',
        'retries',
        'timeout',
        'bulk',
        'payload_config',
        'payload_type',
    ];

    protected $casts = [
        'payload_config' => 'array',
        'headers' => 'array',
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
