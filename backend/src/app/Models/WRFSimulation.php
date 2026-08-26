<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class WRFSimulation extends Model
{
    protected $table = 'wrf_simulations';

    protected $fillable = [
        'name',
        'domain_id',
        'start_date',
        'end_date',
        'simulation_hours',
        'entity_id',
        'status',
    ];

    protected $casts = [
        'start_date' => 'datetime',
        'end_date' => 'datetime',
    ];

    public function domain()
    {
        return $this->belongsTo(WRFDomain::class, 'domain_id');
    }

    public function entity()
    {
        return $this->belongsTo(Entity::class, 'entity_id');
    }
}
