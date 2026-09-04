<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Models\Realtime\EntityCommand;
use App\Models\Realtime\EntityProperty;
use App\Models\FiwareScope;
use App\Traits\Searchable;

class Entity extends AuditableModel
{
    use HasFactory, Searchable;

    protected static array $searchable = ['urn', 'datamodel', 'name'];

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'urn',
        'datamodel',
        'tenant',
        'scope',
        'fiware_scope_id',
    ];

    public function devices()
    {
        return $this->belongsToMany(\App\Models\Device::class)
            ->withTimestamps();
    }
    /**
     * Get the tenant that this entity belongs to.
     */
    public function tenant()
    {
        return $this->belongsTo(\App\Models\FiwareTenant::class);
    }
    /**
     * This is called FiwareScope because there is another column
     * called scope in the entities table, so to avoid conflicts
     * and to be backwards compatible, we call it fiwareScope
     */
    public function fiwareScope()
    {
        return $this->belongsTo(FiwareScope::class, 'fiware_scope_id');
    }

    public function name()
    {
        return $this->hasOne(EntityProperty::class)
            ->where('name', 'name');
    }

    public function geolocation()
    {
        return $this->hasOne(EntityProperty::class)
            ->where('name', 'location');
    }

    public function entityProperties()
    {
        return $this->hasMany(EntityProperty::class);
    }

    public function commands()
    {
        return $this->hasMany(EntityCommand::class);
    }

    public function entityGroups()
    {
        return $this->belongsToMany(\App\Models\EntityGroup::class);
    }


    public function permissions(): \Illuminate\Support\Collection
    {
        $permissions_array = \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);

        $fiware_scope = $this->fiwareScope;

        if ($fiware_scope) {
            $permissions_array = collect($permissions_array)->merge(
                $fiware_scope->permissions()
            );
        }

        $fiware_tenant = $fiware_scope->tenant;

        if ($fiware_tenant) {
            $permissions_array = collect($permissions_array)->merge(
                $fiware_tenant->permissions()
            );
        }

        return $permissions_array;
    }

    public function virtualizations()
    {
        return $this->morphMany(Virtualization::class, 'virtualization');
    }


    public function getLastDataTimestamp(): ?string
    {
        $max = $this->entityProperties()
            ->max('timestamp');

        return $max;
    }
}
