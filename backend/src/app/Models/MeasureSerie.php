<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;
// DB
use Illuminate\Support\Facades\DB;

class MeasureSerie extends AuditableModel
{
    protected $table = 'measure_series';

    protected $fillable = [
        'entity_id',
        'measure',
        'serie_id',
        'visible',
        'grouping_function',
        'grouping_function_value',
        'grouping_interval',
        'grouping_interval_value',
        'period',
        'offset'
    ];

    // measure is a json so $serie->extra_measure->measure = json_decode($serie->extra_measure->measure);
    protected $casts = [
        'measure' => 'array',
        'period' => 'array',
        'offset' => 'array',
    ];

    public function serie()
    {
        return $this->belongsTo(\App\Models\Serie::class);
    }

    public function entity()
    {
        return $this->belongsTo(\App\Models\Entity::class)
            ->with(['devices', 'fiwareScope', 'fiwareScope.tenant', 'geolocation']);
    }
}
