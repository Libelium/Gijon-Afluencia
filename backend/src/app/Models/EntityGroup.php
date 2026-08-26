<?php

namespace App\Models;

use App\Contracts\Limitable;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Models\Realtime\EntityProperty;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class EntityGroup extends AuditableModel implements Limitable
{
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'name',
        'description',
        'user_id',
        'entity_id',
        'type',
        'max_capacity',
        'total_area',
    ];

    public function entities()
    {
        return $this->belongsToMany(\App\Models\Entity::class);
    }

    /**
     * The linked Entity record (e.g. the ParkingGroup entity in the Context Broker).
     */
    public function linkedEntity()
    {
        return $this->belongsTo(Entity::class, 'entity_id');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
