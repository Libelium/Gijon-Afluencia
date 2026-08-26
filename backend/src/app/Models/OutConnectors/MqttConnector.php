<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class MqttConnector extends AuditableModel
{
    protected $table = 'mqtt_connector';

    protected $fillable = [
        'ipAddress',
        'port',
        'username',
        'password',
        'clientId',
        'sslCert',
        'ssl',
        'topicTemplate',
        'payload_type',
        'payload_config',
    ];
    protected $casts = [
        'topicTemplate' => 'array',
        'payload_config' => 'array',
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
