<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use App\Traits\Searchable;

class FiwareScope extends AuditableModel
{
    use Searchable;

    protected static array $searchable = ['name'];

    protected $fillable = [
        'name',
        'fiware_tenant_id',
    ];

    public function tenant(): BelongsTo
    {
        return $this->belongsTo(FiwareTenant::class, 'fiware_tenant_id');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        $permissions_array = \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);

        $fiware_tenant = $this->tenant;

        if ($fiware_tenant) {
            $permissions_array = collect($permissions_array)->merge(
                $fiware_tenant->permissions()
            );
        }

        return $permissions_array;

    }
}