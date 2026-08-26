<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class FiwareOutConnector extends AuditableModel
{
    protected $table = 'fiware_out_connector';

    protected $fillable = [
        'url',
        'iota_type',
        'i',
        'k'
    ];

    protected $casts = [
        'i' => 'array',
        'k' => 'array',
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
