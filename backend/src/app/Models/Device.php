<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Auth;
use App\Traits\Searchable;

class Device extends AuditableModel
{
    use HasFactory, Searchable;

    protected static array $searchable = ['name', 'serial', 'case_id', 'description'];

    protected $primaryKey = 'id';
    public $incrementing = true;

    /*
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'id',
        'serial',
        'case_id',
        'name',
        'description',
        'device_type_id',
        'subscribed_until',
        'properties',
    ];

    protected $hidden = ['id'];

    protected $casts = [
        'properties' => 'object',
    ];

    /**
     * Get the main entity ID for the device.
     *
     * @return int|null
     */
    public function mainEntity()
    {
        return $this->belongsToMany(\App\Models\Entity::class)
            ->with('fiwareScope.tenant')
            ->withPivot('entity_type')
            ->wherePivot('entity_type', 'main')
            ->withTimestamps()
            ->limit(1);
    }

    // Relations
    public function deviceType()
    {
        return $this->belongsTo(\App\Models\DeviceType::class);
    }

    public function users()
    {
        return $this->belongsToMany(\App\Models\User::class)
            ->withPivot('status')
            ->withTimestamps();
    }

    public function organizationOwner()
    {
        return $this->belongsToMany(\App\Models\Organization::class, 'organization_has_resource', 'resource_id', 'organization_id')
            ->withPivot('resource_type', 'resource_id')
            ->wherePivot('resource_type', 'devices')
            ->wherePivot('resource_id', $this->id);
    }


    public function entities()
    {
        return $this->belongsToMany(\App\Models\Entity::class)
            ->withPivot('entity_type')
            ->withTimestamps();
    }

    /**
     * Undocumented function
     *
     * @return void
     */
    protected static function boot()
    {
        parent::boot();

        //Before deleting
        static::deleting(function ($entity) {
            // Delete user relations
            $entity->users()->detach();
        });
    }

    public function permissions(): Collection
    {
        $permissions_array = Auth::user()->getResourcePermissions($this);

        $mainEntity = $this->mainEntity->first();

        if ($mainEntity) {
            $entity_permissions = $mainEntity->permissions();

            // Merge both collections
            $permissions_array = collect($permissions_array)->merge($entity_permissions);
        }

        return collect($permissions_array);
    }

    public function virtualizations()
    {
        return $this->morphMany(Virtualization::class, 'virtualization');
    }
}
