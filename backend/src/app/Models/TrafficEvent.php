<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TrafficEvent extends Model
{
    protected $table = 'traffic_events';

    protected $fillable = [
        'source',
        'event_type',
        'vehicle_type',
        'license_plate_country',
        'license_plate_number',
        'speed',
        'brand',
        'model',
        'color',
        'user_id',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
