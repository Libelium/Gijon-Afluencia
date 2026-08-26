<?php

namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Traits\Searchable;

class InConnector extends AuditableModel implements Limitable
{
    use Searchable;

    protected static array $searchable = ['name', 'type'];
    protected $table = 'in_connectors';

    protected $fillable = [
        'uuid',
        'name',
        'type',
        'status',
        'user_id',
        'last_connection',
        'connectable_type',
        'connectable_id'
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
        return $this->belongsToMany(Entity::class, 'in_connectors_has_entities');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
