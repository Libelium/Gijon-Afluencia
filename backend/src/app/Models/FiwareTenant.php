<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use App\Models\FiwareScope;

class FiwareTenant extends AuditableModel
{
    protected $fillable = [
        'name',
    ];

    public function scopes(): HasMany
    {
        return $this->hasMany(FiwareScope::class);
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}