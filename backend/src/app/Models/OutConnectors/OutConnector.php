<?php

namespace App\Models\OutConnectors;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Models\Entity;
use App\Models\Device;
use App\Models\AuditableModel;
use App\Traits\Searchable;

class OutConnector extends AuditableModel implements Limitable
{
    use Searchable;

    protected static array $searchable = ['name', 'type'];
    protected $table = 'out_connectors';

    protected $fillable = [
        'name',
        'type',
        'status',
        'user_id',
        'last_connection',
        'connectable_type',
        'connectable_id',
        'use_readable_names',
    ];

    public function connectable()
    {
        return $this->morphTo();
    }

    public function getMorphClass()
    {
        return $this->table;
    }

    public function entities()
    {
        return $this->morphedByMany(
            Entity::class,
            'model',
            'out_connectors_has_models',
            'out_connector_id',
            'model_id'
        )->withTimestamps();
    }

    public function devices()
    {
        return $this->morphedByMany(
            Device::class,
            'model',
            'out_connectors_has_models',
            'out_connector_id',
            'model_id',
        )->withTimestamps();
    }

    public function mappingSchemas()
    {
        return  $this->morphedByMany(
            MappingSchema::class,
            'model',
            'out_connectors_has_models',
            'out_connector_id',
            'model_id'
        )
            ->withTimestamps();
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
