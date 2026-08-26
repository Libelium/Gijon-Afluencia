<?php

namespace App\Models;

use App\Models\OutConnectors\MappingSchema; 
use App\Models\Entity;                     
use Illuminate\Database\Eloquent\Model;

class Virtualization extends AuditableModel
{

    protected $fillable = [
        'mapping_schema_id',      
        'destination_entity_id',
        'virtualization_id',
        'virtualization_type',
    ];

    public function virtualization()   
    {
        return $this->morphTo();
    }

    public function mappingSchema()
    {
        return $this->belongsTo(MappingSchema::class, 'mapping_schema_id');
    }

    public function destinationEntity()
    {
        return $this->belongsTo(Entity::class, 'destination_entity_id');
    }
}
