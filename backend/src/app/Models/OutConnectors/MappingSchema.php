<?php

namespace App\Models\OutConnectors;

use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class MappingSchema extends AuditableModel
{
    protected $table = 'mapping_schemas';

    protected $fillable = [
        'name',
        'map'
    ];

    protected $casts = [
        'map' => 'array',
    ];
}
