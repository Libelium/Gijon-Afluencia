<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class LoriotConnector extends AuditableModel
{
    protected $table = 'loriot_connector';

    protected $fillable = [
        'downlink_active',
        'downlink_url',
        'downlink_token',
        'appid'
    ];
    protected $casts = [];

    public function getMorphClass()
    {
        return $this->table;
    }

    public function in_connector()
    {
        return $this->morphOne(InConnector::class, 'connectable');
    }
}
