<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use App\Traits\Searchable;

class Probe extends AuditableModel
{
    use HasFactory;
    use Searchable;

    protected static array $searchable = ['name', 'serial'];

    protected $table = 'probes';

    protected $fillable = [
        'serial',
        'name',
        'probe_type_id',
        'manufacturer',
    ];

    // Relations
    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    // This relation is similar to the user() relation, but we use it to be
    // coherent with Device model and check the owner via: $device->owner->xxxx
    public function owner()
    {
        return $this->belongsTo(\App\Models\User::class, 'user_id', 'id');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }

    public function probeType()
    {
        return $this->belongsTo(ProbeType::class);
    }
}
