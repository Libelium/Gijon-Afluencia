<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ProbeType extends AuditableModel
{
    protected $table = 'probe_types';

    protected $casts = [
        'fiware_properties' => 'array',
    ];

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable =
    [
        'id',
        'name',
        'code',
        'fiware_properties'
    ];

    // Relations
    public function probes()
    {
        return $this->hasMany(\App\Models\Probe::class);
    }
}
