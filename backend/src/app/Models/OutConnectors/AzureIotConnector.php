<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class AzureIotConnector extends AuditableModel
{
    protected $table = 'azureiot_connector';

    protected $fillable = [
        'connection_string',
        'payload_type',
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
