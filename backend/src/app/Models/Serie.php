<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use App\Models\CalculatedSerie;
use App\Models\MeasureSerie;
use App\Models\MultidimensionalSerie;

class Serie extends AuditableModel
{
    protected $table = 'series';

    protected $fillable = [
        'alias',
        'color',
        'type',
        'panel_id',
        'precision',
        'style',
    ];

    protected $hidden = [

    ];

    public function panel()
    {
        return $this->belongsTo(\App\Models\Panel::class);
    }

    public function extra_measure()
    {
        return $this->hasOne(\App\Models\MeasureSerie::class)->with('entity');
    }

    public function extra_calculated()
    {
        return $this->hasOne(\App\Models\CalculatedSerie::class);
    }

    public function extra_multidimensional()
    {
        return $this->hasMany(\App\Models\MultidimensionalSerie::class, 'serie_id')->with('dimension');
    }
}
